# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Complete versioned tool discovery and explicit single-call execution."""
from datetime import datetime, timezone
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import re

from .core.auth import resolve_auth
from .core.evidence import Artifacts, decode
from .core.errors import Failure
from .core.mcp import McpFailure, McpSession, MAX_BYTES

SECRET_FIELDS = {'authorization', 'apikey', 'accesstoken', 'refreshtoken', 'clientsecret',
                 'password', 'cookie', 'secret', 'tokens', 'pollsecret', 'claimtoken'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                     allow_nan=False).encode('utf-8')).hexdigest()


def check_tool(tool):
    if (not isinstance(tool, dict) or not isinstance(tool.get('name'), str)
            or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', tool['name'])
            or not isinstance(tool.get('inputSchema'), dict)
            or tool.get('annotations') is not None and not isinstance(tool['annotations'], dict)):
        raise Failure('Invalid tool definition.')
    def refs(value):
        if isinstance(value, dict):
            for key in ('$ref', '$dynamicRef', '$recursiveRef'):
                if key in value and (not isinstance(value[key], str) or not value[key].startswith('#')):
                    raise Failure('Remote schema references are refused.')
            for child in value.values():
                refs(child)
        elif isinstance(value, list):
            for child in value:
                refs(child)
    refs(tool['inputSchema'])
    return tool


def snapshot(tools, source):
    checked = sorted((check_tool(t) for t in tools), key=lambda t: t['name'])
    if not checked or len(checked) > 4096 or len({t['name'] for t in checked}) != len(checked):
        raise Failure('Tool catalog must contain 1..4096 distinct tools.')
    return {'schemaVersion': 'nexscope.tools.v1', 'source': source,
            'fetchedAt': datetime.now(timezone.utc).isoformat(), 'sha256': digest(checked), 'tools': checked}


def catalog(path=None):
    resource = Path(path) if path else files('nexscope_cli').joinpath('tools.json')
    with resource.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise Failure('Tool catalog exceeds 32 MiB.')
    value = decode(raw)
    if (not isinstance(value, dict) or value.get('schemaVersion') != 'nexscope.tools.v1'
            or not isinstance(value.get('tools'), list) or digest(value['tools']) != value.get('sha256')):
        raise Failure('Tool catalog is missing or has an invalid digest.')
    snapshot(value['tools'], value.get('source'))
    return value


def selected(tools, name):
    matches = [t for t in tools if t['name'] == name or t['name'] == 'nexscope_' + name.replace('-', '_')]
    if len(matches) != 1:
        raise Failure('Unknown or ambiguous tool; use nexscope tools list.')
    return check_tool(matches[0])


def validation_schema(schema):
    """Adapt numeric schema bounds serialized as strings by the Java Long mapper."""
    if isinstance(schema, list):
        return [validation_schema(v) for v in schema]
    if not isinstance(schema, dict):
        return schema
    result = {}
    for key, value in schema.items():
        if key in ('minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf') and isinstance(value, str):
            if not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', value):
                raise Failure('Invalid numeric schema bound.')
            value = json.loads(value)
        result[key] = validation_schema(value) if key not in ('enum', 'const', 'default', 'examples') else value
    return result


def validate(tool, arguments):
    if not isinstance(arguments, dict):
        raise Failure('Tool input must be a JSON object.')
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        raise Failure('Install the declared jsonschema dependency before validating or executing tools.') from None
    from jsonschema.exceptions import SchemaError
    from referencing import Registry
    from referencing.exceptions import NoSuchResource, Unresolvable
    schema = validation_schema(tool['inputSchema'])
    def no_remote(uri):
        raise NoSuchResource(ref=uri)
    try:
        Draft202012Validator.check_schema(schema)
        error = next(Draft202012Validator(schema, registry=Registry(retrieve=no_remote)).iter_errors(arguments), None)
    except (SchemaError, Unresolvable):
        raise Failure('The published tool schema is invalid; execution refused.') from None
    if error:
        path = '/'.join(map(str, error.absolute_path)) or '(root)'
        # Validation messages can contain secret-bearing input values.
        raise Failure('Invalid tool input at ' + path + ': ' + str(error.validator) + ' constraint failed.')


def sanitize(value, context=None):
    if isinstance(value, dict):
        return {context.redact(key) if context else key: '[REDACTED]' if re.sub(r'[-_\s]', '', key).lower() in SECRET_FIELDS
                else sanitize(child, context) for key, child in value.items()}
    if isinstance(value, list):
        return [sanitize(child, context) for child in value]
    if isinstance(value, str):
        if value.lstrip().startswith(('{', '[')):
            try:
                return json.dumps(sanitize(decode(value.encode('utf-8')), context), ensure_ascii=False)
            except Failure:
                pass
        return context.redact(value) if context else value
    return value


def context(args):
    loader = None
    if args.auth_mode == 'browser-account':
        from .main import Client
        client = Client(args.api_base or 'https://api.nexscope.ai')
        loader = lambda: client.load('credential')
    return resolve_auth(args.auth_mode, base=args.api_base, credential_loader=loader)


def origin(value, bundled):
    # The bundled snapshot records an internal export server; show origins only for user-selected catalogs.
    return {} if bundled else {'source': value['source']}


def list_result(value, search='', bundled=False):
    entries = [{'name': t['name'], 'title': t.get('title'), 'description': t.get('description', ''),
                'readOnly': (t.get('annotations') or {}).get('readOnlyHint') is True}
               for t in value['tools'] if search.lower() in (t['name'] + ' ' + (t.get('title') or '')
                                                           + ' ' + (t.get('description') or '')).lower()]
    return {'schemaVersion': 'nexscope.tool-list.v1', 'status': 'CATALOG_READY',
            **origin(value, bundled), 'catalogSha256': value['sha256'],
            'total': len(value['tools']), 'matched': len(entries), 'tools': entries,
            'verification': 'Registered tool schemas; availability and business results depend on the selected server.'}


def command(args):
    if args.tool_action in ('list', 'describe', 'refresh'):
        if args.tool_action == 'refresh' or args.live:
            auth = context(args)
            with McpSession(auth) as session:
                value = snapshot(session.tools(), auth.base)
        else:
            value = catalog(args.catalog)
        bundled = args.tool_action != 'refresh' and not args.live and not args.catalog
        if args.tool_action == 'refresh':
            with Path(args.out).open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(value, stream, ensure_ascii=False, indent=2)
            return {'schemaVersion': 'nexscope.tool-catalog.v1', 'status': 'CATALOG_SAVED',
                    'tools': len(value['tools']), 'sha256': value['sha256'], 'output': str(Path(args.out).resolve())}
        if args.tool_action == 'describe':
            tool = selected(value['tools'], args.tool)
            bindings = decode(files('nexscope_cli').joinpath('api-contract.json').read_bytes())['toolBindings']
            return {'schemaVersion': 'nexscope.tool-description.v1', 'status': 'REGISTERED',
                    'catalogSha256': value['sha256'], **origin(value, bundled),
                    'tool': tool, 'bundledBinding': bindings.get(tool['name']),
                    'execution': 'Explicit --execute and --allow-paid; --allow-write unless read-only is declared. Tool-specific preview/confirmation remains mandatory.'}
        return list_result(value, args.search, bundled)
    value = catalog(args.catalog)
    tool = selected(value['tools'], args.tool)
    with Path(args.input).open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise Failure('Tool input exceeds 32 MiB.')
    arguments = decode(raw)
    validate(tool, arguments)
    plan = {'schemaVersion': 'nexscope.tool-plan.v1', 'status': 'PLAN_READY', 'tool': tool['name'],
            'inputSha256': hashlib.sha256(raw).hexdigest(), 'contractSha256': digest(tool['inputSchema']),
            'catalogSha256': value['sha256'], 'authMode': args.auth_mode, 'maxCalls': 1,
            'automaticRetries': 0, 'estimatedCredits': None, 'networkCalls': 0,
            'requiresWriteApproval': (tool.get('annotations') or {}).get('readOnlyHint') is not True}
    if args.out:
        out = Path(args.out).resolve()
        if out.exists() or not out.parent.is_dir():
            raise Failure('Choose a new output directory with an existing parent.')
    if args.dry_run:
        return plan
    if not args.allow_paid or (plan['requiresWriteApproval'] and not args.allow_write):
        raise Failure('Execution requires --allow-paid and, unless declared read-only, --allow-write. Review the tool contract and any preview/confirmation requirement first.')
    if not args.out:
        raise Failure('Execution requires --out for saved results and evidence.')
    auth = context(args)
    artifacts = Artifacts(out)
    artifacts.write('plan.json', {**plan, 'origin': auth.base})
    artifacts.write('input.json', sanitize(arguments, auth))
    result = {'schemaVersion': 'nexscope.tool-result.v1', 'status': 'FAILED', 'tool': tool['name'],
              'output': str(out), 'requestsSent': 0, 'automaticRetries': 0, 'credits': None,
              'cachePolicy': 'disabled-unverified-tool-semantics', 'result': None, 'error': None}
    session = McpSession(auth)
    try:
        with session:
            live_tool = selected(session.tools(), tool['name'])
            validate(live_tool, arguments)
            if (live_tool.get('annotations') or {}).get('readOnlyHint') is not True and not args.allow_write:
                raise McpFailure('CONFIRMATION_REQUIRED', 'The selected server does not declare this tool read-only.')
            response = sanitize(session.call(tool['name'], arguments), auth)
            artifacts.write('request-1.json', {'schemaVersion': 'nexscope.tool-request.v1',
                            'tool': tool['name'], 'inputSchemaSha256': digest(live_tool['inputSchema']),
                            'response': response, 'fetchedAt': datetime.now(timezone.utc).isoformat()})
            structured = response.get('structuredContent')
            if structured is None:
                for item in response.get('content', []):
                    if isinstance(item, dict) and item.get('type') == 'text':
                        try:
                            candidate = decode(item['text'].encode('utf-8'))
                        except (Failure, KeyError, AttributeError):
                            continue
                        if isinstance(candidate, dict) and ('code' in candidate or 'ok' in candidate):
                            structured = candidate
                            break
            failed = response.get('isError') is True or (isinstance(structured, dict)
                     and (structured.get('ok') is False or structured.get('code', 0) not in (0, '0', None)))
            result.update(status='FAILED' if failed else 'RESULT_READY', result=response)
            if failed:
                result['error'] = {'type': 'TOOL_ERROR', 'message': 'The tool reported a business failure; inspect its saved structured result.'}
    except McpFailure as error:
        result['error'] = {'type': error.kind, 'code': error.code, 'message': str(error)}
        if session.tool_calls and error.kind in ('OUTCOME_UNKNOWN', 'INVALID_RESPONSE', 'UPSTREAM_ERROR'):
            result['status'] = 'OUTCOME_UNKNOWN'
    except Failure:
        result['status'] = 'OUTCOME_UNKNOWN' if session.tool_calls else 'FAILED'
        result['error'] = {'type': 'INVALID_RESPONSE' if session.tool_calls else 'CONTRACT_ERROR',
                           'message': 'The server contract or response could not be validated; no automatic retry.'}
    finally:
        result['requestsSent'] = session.tool_calls
        artifacts.write('result.json', {**result, 'output': '.'})
        artifacts.finish()
    return result
