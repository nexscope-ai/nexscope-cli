# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""A single task entry: plan, optional search, details, evidence and report."""
from datetime import datetime, timezone
import hashlib
import json

from ..capabilities.catalog import DOMAINS
from ..capabilities.plan import plan
from ..core.datasets import product
from ..core.evidence import Artifacts, decode, read_bundle, validate_request
from ..core.errors import Failure
from ..reports.compare import render_format
from ..reports.formats import FORMATS


def read_candidates(folder):
    bundle = read_bundle(folder)
    if set(bundle) != {'plan.json', 'request-1.json', 'candidates.json', 'result.json'}:
        raise Failure('Resume requires a completed candidates-only output; failed calls are never replayed.')
    previous = decode(bundle['plan.json'])
    result = decode(bundle['result.json'])
    search = validate_request(decode(bundle['request-1.json']))
    if (not isinstance(previous, dict) or previous.get('schemaVersion') != 'nexscope.comparison-plan.v1'
            or previous.get('status') != 'PLANNED' or type(previous.get('maxCalls')) is not int
            or previous.get('marketplace') not in DOMAINS
            or previous.get('authMode') not in ('browser-account', 'env-api-key')
            or previous.get('asins') is not None or previous.get('selectedAsins') is not None
            or previous.get('importedSearch') is not None or not previous.get('keyword')
            or not isinstance(result, dict) or result.get('schemaVersion') != 'nexscope.comparison-result.v1'
            or result.get('status') != 'CANDIDATES_READY' or result.get('error') != 'SELECTION_REQUIRED'
            or result.get('sourceType') not in ('mock', 'remote')):
        raise Failure('Resume requires a versioned CANDIDATES_READY comparison checkpoint.')
    rebuilt = workflow_plan(keyword=previous['keyword'], market=previous.get('marketplace'),
                            max_calls=previous.get('maxCalls'), auth_mode=previous.get('authMode'))
    execution = previous.get('execution')
    if (not isinstance(execution, dict) or execution.get('sourceType') != result['sourceType']
            or execution.get('origin') != search['origin'] or execution.get('requestsSent') != 0
            or previous.get('maximumRequests') != 1 or search['capability'] != 'amazon-search'
            or search['status'] != 'SUCCESS' or search['cacheHit'] or search['sequence'] != 1
            or search['authMode'] != rebuilt['authMode'] or search['params'] != rebuilt['steps'][0]['requests'][0]['body']
            or not isinstance(previous.get('steps'), list) or len(previous['steps']) != 1
            or not isinstance(previous['steps'][0], dict)
            or previous['steps'][0].get('requests') != rebuilt['steps'][0]['requests']
            or previous['steps'][0].get('capability') != 'amazon-search'
            or previous['steps'][0].get('contractVersion') != search['contractVersion']
            or previous['steps'][0].get('source') != search['source']
            or not isinstance(previous['steps'][0].get('auth'), dict)
            or previous['steps'][0]['auth'].get('mode') != search['authMode']
            or previous['steps'][0]['auth'].get('origin') != search['origin']
            or (result['sourceType'] == 'mock' and search['origin'] != 'https://mock.invalid')):
        raise Failure('Checkpoint plan and search evidence disagree.')
    candidates = search['response']['data']['products']
    budget = result.get('budget')
    if (decode(bundle['candidates.json']) != candidates or result.get('candidates') != candidates
            or not isinstance(budget, dict) or type(budget.get('requestsSent')) is not int or budget['requestsSent'] != 1
            or budget.get('maxCalls') != rebuilt['maxCalls'] or budget.get('cacheHits') != 0
            or budget.get('stoppedAfterFailure') is not False):
        raise Failure('Checkpoint candidates or accounting disagree with search evidence.')
    return previous, result, search, bundle


def workflow_plan(*, asins=None, keyword=None, resume=None, selected=None, market=None, max_calls=None, auth_mode=None, api_base=None):
    if sum(bool(value) for value in (asins, keyword, resume)) != 1:
        raise Failure('Provide exactly one of asins, keyword or resume.')
    history = None
    if resume:
        previous, result, search, bundle = read_candidates(resume)
        if ((market is not None and market != previous['marketplace'])
                or (auth_mode is not None and auth_mode != previous['authMode'])
                or (api_base is not None and api_base.rstrip('/') != search['origin'])):
            raise Failure('Resume must keep the original marketplace, authentication mode and origin.')
        market, auth_mode = previous['marketplace'], previous['authMode']
        if auth_mode == 'browser-account':
            api_base = search['origin']
        max_calls = previous['maxCalls'] if max_calls is None else max_calls
        if type(max_calls) is not int or max_calls > previous['maxCalls']:
            raise Failure('Resume cannot increase the original max-calls budget.')
        if not selected:
            raise Failure('Resume requires select-asins from the saved candidates.')
        if not set(selected.split(',')) <= {row['asin'] for row in search['response']['data']['products']}:
            raise Failure('Selected ASINs must come from the saved search evidence.')
        history = {'historical': True, 'sourceType': result['sourceType'], 'authMode': search['authMode'],
                   'origin': search['origin'], 'fetchedAt': search['fetchedAt'], 'cacheHit': False,
                   'evidenceFile': 'request-1.json', 'planFile': 'search-plan.json',
                   'planSha256': hashlib.sha256(bundle['plan.json']).hexdigest(), 'requestsSent': 1}
    market = market if market is not None else 'amazon.com'
    auth_mode = auth_mode if auth_mode is not None else 'browser-account'
    max_calls = max_calls if max_calls is not None else 4
    if market not in DOMAINS:
        raise Failure('Choose a supported Amazon marketplace.')
    if selected and not (keyword or resume):
        raise Failure('select-asins is only valid with keyword search.')
    if asins or selected:
        detail = plan('amazon-product-detail', {'asins': asins or selected, 'amazonDomain': market}, auth_mode=auth_mode, max_calls=max_calls, api_base=api_base)
        if len(detail['requests']) < 2:
            raise Failure('A comparison requires two or three distinct ASINs.')
    else:
        detail = None
    search = plan('amazon-search', {'keyword': keyword, 'amazonDomain': market}, auth_mode=auth_mode, max_calls=max_calls, api_base=api_base) if keyword else None
    maximum = (len(detail['requests']) if detail else 0) + (1 if search or history else 0)
    if maximum > max_calls:
        raise Failure('Search plus details exceeds max-calls; no requests were sent.')
    return {'schemaVersion': 'nexscope.comparison-plan.v1', 'status': 'PLANNED',
            'authMode': auth_mode, 'marketplace': market, 'asins': asins, 'keyword': keyword,
            'selectedAsins': selected, 'maximumRequests': maximum, 'maxCalls': max_calls,
            'estimatedCredits': None, 'billingCap': None, 'requestsSent': 1 if history else 0,
            'newRequests': maximum - (1 if history else 0), 'importedSearch': history,
            'selectionPolicy': 'explicit-ASINs-only; otherwise return candidates',
            'steps': [item for item in (search, detail) if item], 'liveExecutionAvailable': False}


def compare(executor, folder, *, asins=None, keyword=None, resume=None, selected=None, market=None, mock=False, format='html', allow_paid=False):
    if not mock and not allow_paid:
        raise Failure('LIVE_EXECUTION_UNAVAILABLE: remote execution requires explicit --allow-paid authorization.')
    source_type = 'mock' if mock else 'remote'
    if format not in (*FORMATS, 'all'):
        raise Failure('Choose html, csv, markdown or all.')
    execution_plan = workflow_plan(asins=asins, keyword=keyword, resume=resume, selected=selected, market=market,
                                   max_calls=executor.max_calls, auth_mode=executor.context.mode,
                                   api_base=executor.context.base if executor.context.mode == 'browser-account' else None)
    market = execution_plan['marketplace']
    if executor.sent or executor.results or executor.imported_results:
        raise Failure('A comparison requires a fresh executor and its own request budget.')
    imported = execution_plan['importedSearch']
    if imported and (imported['sourceType'] != source_type or imported['origin'] != executor.context.base):
        raise Failure('Resume must keep the original source type and authentication origin.')
    execution_plan['execution'] = {'sourceType': source_type, 'origin': executor.context.base, 'requestsSent': 0}
    execution_plan['liveExecutionAvailable'] = allow_paid and not mock
    execution_plan['reportFormat'] = format
    for step in execution_plan['steps']:
        step['auth'].update(origin=executor.context.base, originSource='fictional mock transport' if mock else 'selected authentication context')
    artifacts = Artifacts(folder, execution_plan)
    if resume:
        _, _, historical_search, bundle = read_candidates(resume)
        artifacts.write_bytes('search-plan.json', bundle['plan.json'])
        artifacts.write_bytes('search-result.json', bundle['result.json'])
        for name in ('request-1.json', 'candidates.json'):
            artifacts.write_bytes(name, bundle[name])
        executor.imported_results = [historical_search]
    executor.record = artifacts.record
    chosen = asins or selected
    if keyword:
        search = executor.execute('amazon-search', {'keyword': keyword, 'amazonDomain': market})[0]
        candidates = search['response']['data']['products'] if search['status'] == 'SUCCESS' else []
        artifacts.write('candidates.json', candidates)
        available = {row['asin'] for row in candidates}
        if search['status'] != 'SUCCESS' or not chosen or not set(chosen.split(',')) <= available:
            status = 'CANDIDATES_READY' if search['status'] == 'SUCCESS' and not chosen else 'FAILED'
            result = {'schemaVersion': 'nexscope.comparison-result.v1', 'status': status, 'sourceType': source_type, 'report': None,
                      'error': 'SELECTION_REQUIRED' if status == 'CANDIDATES_READY' else 'SEARCH_OR_SELECTION_FAILED',
                      'candidates': candidates, 'output': str(artifacts.root), 'budget': executor.summary()}
            artifacts.write('result.json', dict(result, output='.'))
            artifacts.finish()
            return result
    details = executor.execute('amazon-product-detail', {'asins': chosen, 'amazonDomain': market})
    rows = [product(result, market) for result in details if result['status'] == 'SUCCESS']
    for row in rows:
        evidence_file = artifacts.root / row['extra']['evidenceFile']
        row['extra']['evidenceSha256'] = hashlib.sha256(evidence_file.read_bytes()).hexdigest()
    errors = [{'asin': result['params']['asins'], 'status': result['status'], 'error': result['error']}
              for result in details if result['status'] != 'SUCCESS']
    status = ('COMPLETE' if not errors else 'PARTIAL') if len(rows) >= 2 else 'INSUFFICIENT_DATA'
    digest = hashlib.sha256((artifacts.root / 'plan.json').read_bytes()).hexdigest()
    dataset = {'schemaVersion': 1, 'sourceType': source_type, 'inputName': 'plan.json', 'inputSha256': digest,
               'importedAt': datetime.now(timezone.utc).isoformat(), 'products': rows,
               'collectionStatus': status, 'errors': errors, 'budget': executor.summary()}
    artifacts.write('dataset.json', dataset)
    result = {'schemaVersion': 'nexscope.comparison-result.v1', 'status': status, 'sourceType': source_type, 'requested': len(chosen.split(',')),
              'succeeded': len(rows), 'errors': errors, 'budget': executor.summary(),
              'output': str(artifacts.root), 'report': None, 'reports': {},
              'liveRequests': 0 if mock else executor.summary()['requestsSent'],
              'liveRequestsThisRun': 0 if mock else executor.sent}
    if len(rows) >= 2:
        # Report beside its evidence; all links stay relative when sharing folder.
        for selected_format in FORMATS if format == 'all' else (format,):
            report = artifacts.root / ('comparison' + FORMATS[selected_format])
            with report.open('x', encoding='utf-8', newline='') as stream:
                stream.write(render_format(dataset, '.', selected_format))
            result['reports'][selected_format] = str(report)
        result['report'] = next(iter(result['reports'].values()))
        result['reportFormat'] = format
    artifacts.write('result.json', dict(result, output='.',
                    report=next((('comparison' + FORMATS[name]) for name in result['reports']), None),
                    reports={name: 'comparison' + FORMATS[name] for name in result['reports']}))
    artifacts.finish()
    return result


def command(args):
    if args.mock and args.api_base is not None:
        raise Failure('Mock workflow uses a fictional origin only; omit --api-base.')
    execution_plan = workflow_plan(asins=args.asins, keyword=args.keyword, resume=args.resume, selected=args.select_asins,
                                   market=args.market, max_calls=args.max_calls, auth_mode=args.auth_mode, api_base=args.api_base)
    args.market, args.max_calls, args.auth_mode = execution_plan['marketplace'], execution_plan['maxCalls'], execution_plan['authMode']
    imported = execution_plan['importedSearch']
    if imported and imported['sourceType'] != ('mock' if args.mock else 'remote'):
        raise Failure('Resume must keep the original source type; choose the same mock or remote execution mode.')
    if args.dry_run:
        execution_plan['reportFormat'] = args.format
        return execution_plan
    if not args.mock and not args.allow_paid:
        raise Failure('LIVE_EXECUTION_UNAVAILABLE: --execute requires --mock or explicit --allow-paid.')
    if args.mock and args.allow_paid:
        raise Failure('Choose mock execution or paid execution, not both.')
    if not args.out:
        raise Failure('Choose a new output directory with --out.')
    if imported and args.auth_mode == 'browser-account':
        args.api_base = imported['origin']
    from ..core.remote import engine_for
    engine = engine_for(args)
    return compare(engine, args.out, asins=args.asins, keyword=args.keyword, resume=args.resume,
                   selected=args.select_asins, market=args.market, mock=bool(args.mock), format=args.format, allow_paid=args.allow_paid)
