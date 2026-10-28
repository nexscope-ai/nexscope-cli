"""Run only from verify_wheel.py's isolated, external working directory."""
from contextlib import redirect_stdout
import importlib.abc
from importlib import metadata
from importlib.resources import files
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import types
import unittest
from unittest.mock import patch

import nexscope_cli
from nexscope_cli.main import main


def cli(*args, expected=0):
    output = io.StringIO()
    with patch('sys.argv', ['nexscope', *map(str, args)]), redirect_stdout(output):
        code = main()
    assert code == expected, (args, code, output.getvalue())
    return json.loads(output.getvalue())


def offline():
    class BlockOnline(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in ('keyring', 'requests'):
                raise AssertionError('Offline command attempted to import ' + fullname)

    blocker = BlockOnline()
    sys.meta_path.insert(0, blocker)
    try:
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline network access')):
            suite = unittest.defaultTestLoader.discover('tests')
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            assert result.wasSuccessful(), 'Installed test suite failed'
            doctor = cli('doctor', '--offline')
            assert doctor['status'] == 'READY_LOCAL', doctor
            catalog = cli('tools', 'list')
            assert catalog['total'] == 565, catalog
            cli('tools', 'describe', 'nexscope_amazon_search')
            cli('report', 'describe')
            cli('report', 'describe', '--schema')
            cli('capabilities', 'describe', 'amazon-search')
            cli('capabilities', 'describe', 'amazon-product-detail')
            cli('get-skills', 'core')
            workflow_guide = cli('get-skills', 'product-comparison')
            assert workflow_guide['ruleSource'] == 'nexscope_cli.workflows.compare'
            for name in ('amazon-search', 'amazon-product-detail'):
                cli('get-skills', name)
            cli('report', 'template', '--out', 'template.csv')
            for suffix in ('csv', 'json'):
                source = '自有 data.' + suffix
                cli('report', 'demo', '--format', suffix, '--out', source)
                for format, extension in [('html', '.html'), ('csv', '.csv'), ('markdown', '.md')]:
                    output = suffix + format + extension
                    cli('report', 'compare', '--input', source, '--format', format, '--out', output)
                    cli('report', 'compare', '--input', output + '.evidence/dataset.json',
                        '--format', format, '--out', '再导出 ' + output)
            cli('demo', 'product-comparison', '--out', 'demo')
            cli('workflow', 'compare', '--keyword', 'lamp', '--dry-run')
            cli('workflow', 'compare', '--keyword', 'lamp', '--execute', '--mock', 'complete',
                '--max-calls', '3', '--out', 'candidates')
            cli('workflow', 'compare', '--resume', 'candidates', '--select-asins', 'B000000001,B000000002',
                '--dry-run', '--mock', 'complete')
            resumed = cli('workflow', 'compare', '--resume', 'candidates', '--select-asins', 'B000000001,B000000002',
                          '--execute', '--mock', 'complete', '--format', 'all', '--out', 'finished')
            assert resumed['budget']['requestsSent'] == 3 and resumed['budget']['importedRequests'] == 1
            cli('report', 'compare', '--input', 'finished/dataset.json', '--out', 'resumed.html')
            cli('workflow', 'compare', '--asins', 'A,B,C', '--execute', '--mock', 'partial', '--out', 'partial')
            cli('workflow', 'compare', '--asins', 'B000000001,B000000002,B000000003', '--execute',
                '--mock', 'partial', '--out', 'real-partial', expected=1)
            Path('params.json').write_text('{"keyword":"lamp"}')
            cli('data', 'run', 'amazon-search', '--input', Path('params.json').resolve(), '--dry-run')
            assert 'keyring' not in sys.modules and 'requests' not in sys.modules
        return result.testsRun
    finally:
        sys.meta_path.remove(blocker)


def loopback(with_dependencies=False):
    records = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else None
            records.append((self.path, self.headers.get('Authorization'), body))
            if body and body.get('keyword') == 'redirect':
                self.send_response(302)
                self.send_header('Location', '/trap')
                self.end_headers()
                return
            if self.path.endswith('/auth/start'):
                data = {'requestId': 'fixture-request', 'pollSecret': 'fixture-poll',
                        'expiresAt': '9999999999999', 'loginUrl': 'https://example.invalid/fictional', 'status': 'AUTH_REQUIRED'}
            elif self.path.endswith('/auth/poll'):
                data = {'status': 'READY', 'apiKey': 'fixture-browser'}
            elif self.path.endswith('/account'):
                data = {'accountId': 'fixture-account', 'rechargeUrl': 'https://example.invalid/fictional'}
            elif self.path.endswith('/disconnect'):
                data = {'status': 'DISCONNECTED'}
            else:
                asins = body.get('asins', 'B000000001,B000000002,B000000003').split(',')
                data = {'products': [{'asin': asin, 'title': 'Fictional ' + asin, 'price': 19.99,
                                      'currency': 'USD', 'rating': 4, 'ratingScale': 5, 'ratings': 10}
                                     for asin in asins]}
            raw = json.dumps({'code': 0, 'data': data}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    environment = dict(os.environ, NEXSCOPE_API_KEY='fixture-env', NEXSCOPE_PROXY_BASE=base)
    try:
        with patch.dict(os.environ, environment, clear=True):
            cli('workflow', 'compare', '--asins', 'B000000001,B000000002', '--auth-mode', 'env-api-key',
                '--execute', '--allow-paid', '--out', 'env-http')
            cli('report', 'compare', '--input', 'env-http/dataset.json', '--out', 'env-offline.html')
            cli('workflow', 'compare', '--keyword', 'lamp', '--auth-mode', 'env-api-key',
                '--execute', '--allow-paid', '--out', 'env-candidates')
            resumed = cli('workflow', 'compare', '--resume', 'env-candidates', '--select-asins', 'B000000001,B000000002',
                          '--execute', '--allow-paid', '--out', 'env-resumed')
            assert resumed['budget']['importedRequests'] == 1 and resumed['liveRequestsThisRun'] == 2
            cli('workflow', 'compare', '--keyword', 'redirect', '--auth-mode', 'env-api-key',
                '--execute', '--allow-paid', '--out', 'redirect-refused', expected=1)
            assert not any(path == '/trap' for path, auth, body in records)
            assert all(auth == 'Bearer fixture-env' for path, auth, body in records)
            records.clear()

            class Store:
                __module__ = 'keyring.backends.Windows'

                def __init__(self):
                    self.values = {}

                def get_password(self, service, name):
                    return self.values.get((service, name))

                def set_password(self, service, name, value):
                    self.values[service, name] = value

                def delete_password(self, service, name):
                    del self.values[service, name]

            store = Store()
            keyring = types.ModuleType('keyring')
            keyring.get_keyring = lambda: store
            with patch.dict(sys.modules, keyring=keyring):
                start = cli('--api-base', base, 'auth', 'login', '--source-client', 'python-cli')
                assert 'pollSecret' not in start
                account = cli('--api-base', base, 'auth', 'poll')
                assert account['accountId'] == 'fixture-account' and 'apiKey' not in account
                cli('--api-base', base, 'workflow', 'compare', '--keyword', 'lamp', '--execute',
                    '--allow-paid', '--out', 'browser-candidates')
                resumed = cli('workflow', 'compare', '--resume', 'browser-candidates',
                              '--select-asins', 'B000000001,B000000002', '--execute', '--allow-paid', '--out', 'browser-http')
                assert resumed['liveRequests'] == 3 and resumed['liveRequestsThisRun'] == 2
                if with_dependencies:
                    legacy = cli('--api-base', base, 'run', 'amazon-search', '--output', 'old-browser',
                                 '--', '{"keyword":"lamp","page":8}', '--inline', '--no-cache')
                    assert legacy['status'] == 'OUTPUT_READY', legacy
                cli('--api-base', base, 'auth', 'logout')
                # One-step sign-in waits for the fixture to approve, then returns the account.
                account = cli('--api-base', base, 'login', '--no-browser')
                assert account['accountId'] == 'fixture-account' and 'apiKey' not in account
                cli('--api-base', base, 'auth', 'logout')
            assert not store.values
            protected = [(path, auth) for path, auth, body in records if not path.endswith(('/auth/start', '/auth/poll'))]
            assert protected and all(auth == 'Bearer fixture-browser' for path, auth in protected)

        for name, script, params in [('amazon-search', 'amazon_search.py', {'keyword': 'lamp', 'page': 8}),
                                     ('amazon-product-detail', 'amazon_product_detail.py', {'asins': 'A,B,C,D'})]:
            entry = files('nexscope_cli').joinpath('skills', name, 'scripts', script)
            completed = subprocess.run([sys.executable, '-I', str(entry), json.dumps(params), '--inline', '--no-cache'],
                                       env=environment, capture_output=True, text=True, encoding='utf-8')
            assert completed.returncode == 0, completed.stderr
            assert 'Saved full response:' in completed.stdout
            assert records[-1][1:] == ('Bearer fixture-env', params)
        return len(records)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    installed = Path(nexscope_cli.__file__).resolve()
    assert installed.is_relative_to(Path(sys.prefix).resolve()), installed
    assert metadata.version('nexscope-cli') == nexscope_cli.__version__
    tests = offline() if '--loopback-only' not in sys.argv else 0
    calls = loopback(with_dependencies='--with-dependencies' in sys.argv)
    print(json.dumps({'status': 'PASSED', 'installedModule': str(installed), 'tests': tests,
                      'loopbackCalls': calls, 'version': nexscope_cli.__version__, 'liveServiceCalls': 0}))
