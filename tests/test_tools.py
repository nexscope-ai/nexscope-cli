"""Full-catalog and MCP regressions with an injected HTTP peer; no network."""
from contextlib import contextmanager, redirect_stdout
from email.message import Message
import importlib.util
import io
import json
from pathlib import Path
import socket
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from nexscope_cli.core.auth import AuthContext
from nexscope_cli.core.errors import Failure
from nexscope_cli.core.evidence import read_bundle
from nexscope_cli.core.mcp import McpFailure, McpSession
from nexscope_cli import tools

HAS_SCHEMA = importlib.util.find_spec('jsonschema') is not None


class Response(io.BytesIO):
    def __init__(self, payload=b'', status=200, content_type='application/json'):
        super().__init__(payload)
        self.status = status
        self.headers = Message()
        self.headers['Content-Type'] = content_type
        self.headers['Mcp-Session-Id'] = 'fixture-session'


@contextmanager
def peer(mode='success'):
    records = []
    catalog = tools.catalog()['tools']
    names = {t['name'] for t in catalog}
    class Opener:
        def open(self, request, timeout):
            if request.method == 'DELETE':
                return Response(status=204)
            body = json.loads(request.data)
            records.append((body, request.get_header('Authorization'), request.full_url))
            if mode in ('redirect', 'forbidden'):
                raise HTTPError(request.full_url, 302 if mode == 'redirect' else 403, 'fixture', {}, None)
            method = body['method']
            if method == 'notifications/initialized':
                return Response(status=202)
            if method == 'initialize':
                value = {'protocolVersion': '2025-03-26', 'capabilities': {}}
            elif method == 'tools/list':
                value = {'tools': catalog[:2], 'nextCursor': 'next'} if not body['params'] else {'tools': catalog[2:]}
                if mode == 'cursor-loop':
                    value = {'tools': [], 'nextCursor': 'next'}
            else:
                assert method == 'tools/call' and body['params']['name'] in names
                data = {'code': 13007 if mode in ('business-error', 'text-business-error') else 0,
                        'data': {'tool': body['params']['name'], 'value': 'fixture-api-key',
                                 'accessToken': 'private-fixture-token'}}
                value = {'isError': mode == 'business-error', 'structuredContent': data,
                         'content': [{'type': 'text', 'text': json.dumps(data)}]}
                if mode == 'text-business-error':
                    del value['structuredContent']
            payload = json.dumps({'jsonrpc': '2.0', 'id': body['id'], 'result': value}).encode()
            if mode == 'invalid-response' and method == 'tools/call':
                payload = b'{invalid-json'
            if method == 'tools/call':
                prefix = b': heartbeat\n\ndata: {"jsonrpc":"2.0","method":"notifications/progress"}\n\n'
                return Response(prefix + (b'data: ' + payload + b'\n\n' if mode != 'disconnect' else b''),
                                content_type='text/event-stream')
            return Response(payload)
    with patch('nexscope_cli.core.mcp.build_opener', return_value=Opener()):
        yield records


class ToolTests(unittest.TestCase):
    def test_complete_snapshot_has_all_tool_families(self):
        value = tools.catalog()
        self.assertEqual(len(value['tools']), 565)
        self.assertEqual(value['sha256'], tools.digest(value['tools']))
        names = {t['name'] for t in value['tools']}
        for name in ('nexscope_amazon_search', 'nexscope_data_alibaba1688_invoice_apply',
                     'nexscope_seo_keyword_metrics', 'nexscope_whitebg_image', 'nexscope_workflow_read'):
            self.assertIn(name, names)

    @unittest.skipUnless(HAS_SCHEMA, 'Install the declared JSON Schema dependency')
    def test_all_565_input_schemas_validate_without_network(self):
        from jsonschema import Draft202012Validator
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')):
            for tool in tools.catalog()['tools']:
                with self.subTest(tool=tool['name']):
                    Draft202012Validator.check_schema(tools.validation_schema(tool['inputSchema']))

    def test_external_references_and_tampered_catalogs_are_refused(self):
        for keyword in ('$ref', '$dynamicRef'):
            with self.assertRaises(Failure):
                tools.check_tool({'name': 'bad', 'inputSchema': {keyword: 'https://example.invalid/schema'}})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalog.json'
            value = tools.catalog()
            value['tools'].pop()
            path.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaises(Failure):
                tools.catalog(path)

    @unittest.skipUnless(HAS_SCHEMA, 'Install the declared JSON Schema dependency')
    def test_numeric_bounds_preserve_string_identifiers_and_do_not_leak_input(self):
        tool = {'name': 'fixture', 'inputSchema': {'type': 'object', 'required': ['count'],
                'properties': {'count': {'type': 'integer', 'maximum': '9223372036854775807'},
                               'id': {'enum': ['001']}}}}
        tools.validate(tool, {'count': 1, 'id': '001'})
        with self.assertRaises(Failure) as error:
            tools.validate(tool, {'count': 'secret-credential'})
        self.assertNotIn('secret-credential', str(error.exception))
        self.assertEqual(tools.validation_schema(tool['inputSchema'])['properties']['id']['enum'], ['001'])

    @unittest.skipUnless(HAS_SCHEMA, 'Install the declared JSON Schema dependency')
    def test_dry_run_and_discovery_do_not_load_auth_or_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text('{"action":"catalog"}', encoding='utf-8')
            args = SimpleNamespace(tool_action='call', catalog=None, tool='nexscope_workflow_read',
                   input=str(path), out=str(Path(directory) / 'new'), dry_run=True,
                   auth_mode='env-api-key', api_base=None)
            with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')), \
                    patch('nexscope_cli.tools.context', side_effect=AssertionError('Auth forbidden')):
                self.assertEqual(tools.command(args)['networkCalls'], 0)
                args.tool_action, args.live, args.search = 'list', False, 'amazon'
                result = tools.command(args)
                self.assertGreater(result['matched'], 2)
                self.assertEqual(result['total'], 565)
            self.assertFalse((Path(directory) / 'new').exists())

    def test_json_initialize_paginated_discovery_sse_result_and_budget(self):
        with peer() as records:
            with McpSession(AuthContext('env-api-key', 'https://example.invalid', 'fixture-api-key')) as session:
                self.assertEqual(len(session.tools()), 565)
                self.assertFalse(session.call('nexscope_amazon_search', {'keyword': 'fixture'})['isError'])
                with self.assertRaises(McpFailure):
                    session.call('nexscope_amazon_search', {'keyword': 'fixture'})
            self.assertEqual(sum(r[0]['method'] == 'tools/call' for r in records), 1)
            self.assertTrue(all(auth == 'Bearer fixture-api-key' for _, auth, _ in records))

    def test_all_tool_names_dispatch_without_renaming_or_argument_loss(self):
        with peer() as records:
            session = McpSession(AuthContext('env-api-key', 'https://example.invalid', 'fixture-api-key'))
            for index, tool in enumerate(tools.catalog()['tools']):
                result = session.request('tools/call', {'name': tool['name'], 'arguments': {'fixtureIndex': index}})
                self.assertEqual(result['structuredContent']['data']['tool'], tool['name'])
                self.assertEqual(records[-1][0]['params']['arguments'], {'fixtureIndex': index})
            self.assertEqual(len(records), 565)

    def test_http_failures_cursor_loops_and_disconnect_do_not_replay(self):
        for mode, kind in [('redirect', 'HTTP_ERROR'), ('forbidden', 'PERMISSION_DENIED'),
                           ('cursor-loop', 'INVALID_RESPONSE'), ('disconnect', 'OUTCOME_UNKNOWN')]:
            with self.subTest(mode=mode), peer(mode) as records:
                with self.assertRaises(McpFailure) as error:
                    with McpSession(AuthContext('env-api-key', 'https://example.invalid', 'fixture-api-key')) as session:
                        if mode == 'cursor-loop':
                            session.tools()
                        elif mode == 'disconnect':
                            session.call('nexscope_amazon_search', {'keyword': 'fixture'})
                self.assertEqual(error.exception.kind, kind)
                self.assertTrue(all(url == 'https://example.invalid/api/skill-api/v2/mcp' for _, _, url in records))
                self.assertLessEqual(sum(r[0]['method'] == 'tools/call' for r in records), 1)

    @unittest.skipUnless(HAS_SCHEMA, 'Install the declared JSON Schema dependency')
    def test_execution_saves_redacted_evidence_and_preserves_business_failures(self):
        for mode in ('success', 'business-error', 'text-business-error', 'disconnect', 'invalid-response'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory, peer(mode) as records:
                path = Path(directory) / 'input.json'
                path.write_text('{"keyword":"fixture"}', encoding='utf-8')
                args = SimpleNamespace(tool_action='call', catalog=None, tool='nexscope_amazon_search',
                       input=str(path), out=str(Path(directory) / 'result'), dry_run=False,
                       auth_mode='env-api-key', api_base=None, allow_paid=True, allow_write=True)
                with patch('nexscope_cli.tools.context', return_value=AuthContext('env-api-key', 'https://example.invalid', 'fixture-api-key')):
                    result = tools.command(args)
                self.assertEqual(result['status'], {'success': 'RESULT_READY', 'business-error': 'FAILED',
                                'text-business-error': 'FAILED', 'disconnect': 'OUTCOME_UNKNOWN',
                                'invalid-response': 'OUTCOME_UNKNOWN'}[mode])
                self.assertEqual(result['requestsSent'], 1)
                bundle = read_bundle(Path(args.out))
                saved = b'\n'.join(bundle.values()).decode()
                self.assertNotIn('fixture-api-key', saved)
                self.assertNotIn('private-fixture-token', saved)
                self.assertNotIn('private-fixture-token', json.dumps(result))
                self.assertEqual(sum(r[0]['method'] == 'tools/call' for r in records), 1)

    def test_bindings_cover_all_schemas_and_keep_legacy_routes(self):
        from importlib.resources import files
        contract = json.loads(files('nexscope_cli').joinpath('api-contract.json').read_text(encoding='utf-8'))
        self.assertEqual(set(contract['toolBindings']), {t['name'] for t in tools.catalog()['tools']})
        for tool in tools.catalog()['tools']:
            self.assertEqual(contract['toolBindings'][tool['name']]['inputSchemaSha256'], tools.digest(tool['inputSchema']))
        self.assertEqual(contract['routes']['amazon-search']['research'], '/api/v1/tools/research/amazon/search')

    def test_bundled_snapshot_hides_export_origin_but_explicit_catalog_keeps_it(self):
        from importlib.resources import files
        args = SimpleNamespace(tool_action='list', catalog=None, live=False, search='amazon', tool='nexscope_amazon_search')
        self.assertNotIn('source', tools.command(args))
        args.tool_action = 'describe'
        self.assertNotIn('source', tools.command(args))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'current-tools.json'
            value = json.loads(files('nexscope_cli').joinpath('tools.json').read_text(encoding='utf-8'))
            value['source'] = 'https://selected.example'
            path.write_text(json.dumps(value), encoding='utf-8')
            args.catalog = str(path)
            self.assertEqual(tools.command(args)['source'], 'https://selected.example')
            args.tool_action = 'list'
            self.assertEqual(tools.command(args)['source'], 'https://selected.example')

    def test_skill_runs_reenter_a_standalone_binary(self):
        from nexscope_cli.main import ROOT, launcher
        self.assertEqual(launcher(), [sys.executable, str(ROOT / 'runner.py')])
        with patch.object(sys, 'frozen', True, create=True):
            self.assertEqual(launcher(), [sys.executable, '--nexscope-runner'])

    def test_shared_guide_errors_and_provenance_are_offline_and_versioned(self):
        from nexscope_cli.main import main
        from nexscope_cli import __version__
        from nexscope_cli.core.attribution import source, headers
        self.assertEqual(source()['clientVersion'], __version__)
        self.assertEqual(source('codex-plugin', 'marketplace', 'plugin')['client'], 'codex-plugin')
        self.assertEqual(headers()['X-Nexscope-Client-Version'], __version__)
        with self.assertRaises(ValueError):
            source('arbitrary-secret')
        for args, code in [(['get-skills', 'product-comparison'], 0), (['tools', 'describe', 'not-a-tool'], 1)]:
            output = io.StringIO()
            with patch.object(sys, 'argv', ['nexscope', *args]), redirect_stdout(output), \
                    patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')):
                self.assertEqual(main(), code)
            value = json.loads(output.getvalue())
            if code:
                self.assertEqual(value['schemaVersion'], 'nexscope.error.v1')
                self.assertIn('help', value['error'])
            else:
                self.assertEqual(value['ruleSource'], 'nexscope_cli.workflows.compare')

    @unittest.skipUnless(HAS_SCHEMA, 'Install the declared JSON Schema dependency')
    def test_effect_approval_and_existing_output_refuse_before_auth(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text('{"keyword":"fixture"}', encoding='utf-8')
            args = SimpleNamespace(tool_action='call', catalog=None, tool='nexscope_amazon_search',
                   input=str(path), out=str(Path(directory) / 'result'), dry_run=False,
                   auth_mode='env-api-key', api_base=None, allow_paid=False, allow_write=False)
            with patch('nexscope_cli.tools.context', side_effect=AssertionError('Auth forbidden')):
                for paid, write in [(False, False), (True, False)]:
                    args.allow_paid, args.allow_write = paid, write
                    with self.assertRaises(Failure):
                        tools.command(args)
                args.allow_paid, args.allow_write = True, True
                Path(args.out).mkdir()
                with self.assertRaises(Failure):
                    tools.command(args)


if __name__ == '__main__':
    unittest.main()
