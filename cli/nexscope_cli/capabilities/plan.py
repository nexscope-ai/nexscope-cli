# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Pure, bounded request planning. No credential, cache, or transport access."""
import hashlib
import json
from pathlib import Path
import re

from .catalog import describe
from ..core.auth import DEFAULT_ORIGIN, MODES, origin
from ..core.errors import Failure

MAX_INPUT_BYTES = 64 * 1024


def read_input(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise Failure('Plan input exceeds 64 KiB.')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError

    try:
        params = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                            parse_constant=reject_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise Failure('Plan input must be UTF-8 JSON without duplicate keys or non-finite values.') from None
    return params, hashlib.sha256(raw).hexdigest()


def normalize(params, description):
    schema = description['inputSchema']
    if not isinstance(params, dict):
        raise Failure('Plan input must be a JSON object.')
    # Do not echo unknown fields or invalid values: they may contain secrets.
    if set(params) - set(schema['properties']):
        raise Failure('Unsupported parameter; use capabilities describe for allowed fields.')
    if any(key not in params for key in schema['required']):
        raise Failure('Missing required parameters; use capabilities describe.')
    result = {}
    for key, rule in schema['properties'].items():
        if key not in params:
            if 'default' in rule:
                result[key] = rule['default']
            continue
        value = params[key]
        valid = True
        if rule['type'] == 'string':
            valid = isinstance(value, str) and bool(value.strip()) and not any(ord(c) < 32 for c in value)
            if valid:
                valid = len(value) <= rule.get('maxLength', 1000)
                if 'pattern' in rule:
                    valid = valid and re.fullmatch(rule['pattern'], value) is not None
        elif rule['type'] == 'integer':
            valid = type(value) is int
        elif rule['type'] == 'boolean':
            valid = type(value) is bool
        if not valid or ('enum' in rule and value not in rule['enum']):
            raise Failure('Invalid parameter: ' + key + '; see the planning input schema.')
        result[key] = value
    if description['capability'] == 'amazon-search' and not any(k in result for k in ('keyword', 'node')):
        raise Failure('The search pilot requires keyword or node.')
    if 'asins' in result:
        asins = result['asins'].split(',')
        if len(set(asins)) != len(asins):
            raise Failure('Duplicate ASINs are not allowed in the detail plan.')
    return result


def plan(name, params, *, auth_mode='browser-account', api_base=None, max_calls=3):
    description = describe(name)
    if auth_mode not in MODES:
        raise Failure('Choose an explicit supported authentication mode.')
    if type(max_calls) is not int or max_calls < 1:
        raise Failure('max-calls must be a positive integer.')
    if auth_mode == 'env-api-key' and api_base is not None:
        raise Failure('env-api-key resolves NEXSCOPE_PROXY_BASE at execution; omit --api-base.')
    params = normalize(params, description)
    bodies = [dict(params, asins=asin) for asin in params['asins'].split(',')] if name == 'amazon-product-detail' else [params]
    if len(bodies) > max_calls:
        raise Failure('Request count exceeds max-calls; no requests were sent.')
    selected_origin = origin(api_base if api_base is not None else DEFAULT_ORIGIN) if auth_mode == 'browser-account' else None
    return {
        'schemaVersion': 'nexscope.plan.v1', 'status': 'PLANNED',
        'capability': name, 'contractVersion': description['contractVersion'],
        'source': description['source'], 'executionAvailable': False,
        'auth': {'mode': auth_mode, 'origin': selected_origin,
                 'originSource': '--api-base or default' if selected_origin else 'NEXSCOPE_PROXY_BASE at execution',
                 'credentialsRead': False},
        'requests': [{'sequence': i + 1, 'method': 'POST', 'endpoint': description['endpoint'], 'body': body}
                     for i, body in enumerate(bodies)],
        'budget': {'scope': 'data-api-requests-only', 'maxCalls': max_calls, 'plannedRequests': len(bodies),
                   'maximumRequests': len(bodies), 'requestsSent': 0,
                   'automaticRetries': 0, 'estimatedCredits': None,
                   'billingCap': None, 'pricingStatus': 'UNKNOWN', 'pricingSource': None,
                   'note': 'Request bounds are not a monetary or server billing cap.'},
        'cache': {'policy': 'no-cache-read-or-write', 'assumedHits': 0},
        'warnings': ['Remote execution requires explicit --execute --allow-paid; mock never reads credentials.',
                     'No automatic pagination, ASIN expansion, or fallback authentication.'],
    }


def command(args):
    if args.execute and not args.mock and not args.allow_paid:
        raise Failure('EXECUTION_UNAVAILABLE: choose --mock or explicitly authorize remote scope with --allow-paid.')
    params, digest = read_input(args.input)
    result = plan(args.capability, params, auth_mode=args.auth_mode,
                  api_base=args.api_base, max_calls=args.max_calls)
    result['inputSha256'] = digest
    if args.execute:
        if args.mock and args.api_base is not None:
            raise Failure('Mock execution uses a fictional origin; omit --api-base.')
        if not args.out:
            raise Failure('Choose a new output directory with --out.')
        from ..core.remote import engine_for
        if args.mock and args.allow_paid:
            raise Failure('Choose mock execution or paid execution, not both.')
        source_type = 'mock' if args.mock else 'remote'
        from ..core.evidence import Artifacts
        engine = engine_for(args)
        result['execution'] = {'sourceType': source_type, 'origin': engine.context.base, 'requestsSent': 0}
        result['auth'].update(origin=engine.context.base, originSource='selected execution context')
        artifacts = Artifacts(args.out, result)
        engine.record = artifacts.record
        requests = engine.execute(args.capability, params)
        successes = sum(r['status'] == 'SUCCESS' for r in requests)
        result = {'status': 'COMPLETE' if successes == len(requests) else ('PARTIAL' if successes else 'FAILED'),
                  'sourceType': source_type, 'output': str(artifacts.root), 'requests': requests,
                  'budget': engine.summary(), 'liveRequests': 0 if args.mock else engine.sent}
        artifacts.write('result.json', dict(result, output='.'))
        artifacts.finish()
    return result
