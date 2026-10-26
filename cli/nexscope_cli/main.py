# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Independent, OS-keyring-backed Nexscope CLI. Never prints credentials."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

from . import __version__
from .core.datasets import DatasetError
from .core.auth import DEFAULT_ORIGIN, MODES, origin, resolve_auth
from .core.errors import AuthRequired, Failure

ROOT = Path(__file__).parent


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Failure('Redirect refused; check the API origin.')


class Client:
    def __init__(self, base):
        self.base = origin(base)
        import keyring
        backend = keyring.get_keyring()
        # Fail closed: do not fall back to plaintext files or inherited API keys.
        module = type(backend).__module__
        if module not in ('keyring.backends.macOS', 'keyring.backends.Windows', 'keyring.backends.SecretService', 'keyring.backends.kwallet'):
            raise Failure('An OS credential store is required. Configure a supported keyring backend.')
        self.store = backend
        self.service = 'nexscope-cli:' + self.base

    def load(self, name):
        raw = self.store.get_password(self.service, name)
        return json.loads(raw) if raw else None

    def save(self, name, value):
        self.store.set_password(self.service, name, json.dumps(value))

    def clear(self, name):
        if self.load(name) is not None:
            self.store.delete_password(self.service, name)

    def api(self, path, body=None, authenticated=False, context=None):
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if authenticated:
            context = context or resolve_auth('browser-account', base=self.base, credential_loader=lambda: self.load('credential'))
            if context.mode != 'browser-account' or context.base != self.base:
                raise Failure('Browser API requires its own origin-bound browser-account context.')
            headers['Authorization'] = context.authorization()
        req = Request(self.base + '/api/cli/' + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            with build_opener(NoRedirect()).open(req, timeout=30) as response:
                result = json.load(response)
        except HTTPError as e:
            e.close()
            if e.code == 401 and authenticated:
                raise AuthRequired('AUTH_REQUIRED: reconnect with nexscope auth login.') from None
            raise Failure(f'HTTP {e.code}; request not retried.') from None
        except (URLError, TimeoutError):
            raise Failure('Network unavailable; request not retried.') from None
        if not isinstance(result, dict):
            raise Failure('Invalid API response.')
        if result.get('code') in (12001, 12003):
            raise AuthRequired('AUTH_REQUIRED: reconnect with nexscope auth login.')
        if result.get('code') != 0:
            raise Failure(f"API error {result.get('code')}; request not retried.")
        return result.get('data')

    def auth(self, action, attribution=None):
        if action == 'login':
            if self.load('credential'):
                try:
                    return self.api('account', authenticated=True)
                except AuthRequired:
                    self.clear('credential')
            pending = self.load('pending')
            import time
            if not pending or int(pending['expiresAt']) <= time.time() * 1000:
                pending = self.api('auth/start', {} if attribution is None else {'attribution': attribution})
                self.save('pending', pending)
            return {k: v for k, v in pending.items() if k != 'pollSecret'}
        if action == 'poll':
            pending = self.load('pending')
            if not pending:
                return self.api('account', authenticated=True)
            body = {k: pending[k] for k in ('requestId', 'pollSecret')}
            value = self.api('auth/poll', body)
            if value['status'] == 'READY':
                self.save('credential', value)
                self.api('auth/poll', {**body, 'acknowledge': True})
                self.clear('pending')
                return self.api('account', authenticated=True)
            if value['status'] in ('DENIED', 'AUTH_EXPIRED', 'CONNECTED'):
                self.clear('pending')
            return {k: v for k, v in value.items() if k != 'apiKey'}
        if action == 'logout':
            if self.load('credential'):
                self.api('disconnect', {}, authenticated=True)
            self.clear('credential')
            self.clear('pending')
            return {'status': 'DISCONNECTED'}
        return self.api('account', authenticated=True)


def catalog():
    return json.loads((ROOT / 'catalog.json').read_text())['skills']


def guide(name):
    skills = catalog()
    if name == 'core':
        return {'version': __version__, 'skills': {k: v['description'] for k, v in skills.items() if v.get('available', True)},
                'unavailable': {k: v['unavailable'] for k, v in skills.items() if not v.get('available', True)},
                'execution': 'Read get-skills <name>; use run <name> [--script path] -- <script arguments>. Never run packaged scripts directly. Auth: login, user done, poll. Credits: account, link, user done, account.'}
    if name not in skills:
        raise Failure('Unknown skill; use get-skills core.')
    if not skills[name].get('available', True):
        return {'status': 'UNAVAILABLE', 'skill': name, **skills[name]['unavailable']}
    return {'skill': name, 'resourceDirectory': str(ROOT / 'skills' / name), 'scripts': skills[name]['scripts'], 'instructions': (ROOT / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8'),
            'execution': 'Replace python script.py with nexscope run ' + name + ' --script <listed script> -- . Relative input paths must be absolute because runs use isolated output directories.'}


def run(args, client):
    entry = catalog().get(args.skill)
    if not entry:
        raise Failure('Unknown skill.')
    if not entry.get('available', True):
        raise Failure('UNAVAILABLE: ' + entry['unavailable']['reason'])
    script = args.script or (entry['scripts'][0] if len(entry['scripts']) == 1 else None)
    if script not in entry['scripts']:
        raise Failure('Choose --script from get-skills output.')
    context = resolve_auth('browser-account', base=client.base, credential_loader=lambda: client.load('credential'))
    account = client.api('account', authenticated=True, context=context)
    folder = Path(args.output).resolve() / str(uuid.uuid4())
    folder.mkdir(parents=True, mode=0o700)
    env = context.script_environment()
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    # No automatic replay: scripts may create reports, change ads, or consume credits.
    result = subprocess.run([sys.executable, str(ROOT / 'runner.py'), str(ROOT / 'skills' / args.skill / script), *arguments], cwd=folder, env=env, capture_output=True, text=True)
    output = context.redact(result.stdout + result.stderr)
    (folder / 'output.txt').write_text(output)
    files = list(folder.rglob('*.json'))
    failures = []
    for path in files:
        try:
            raw = path.read_text()
            cleaned = context.redact(raw)
            if raw != cleaned:
                path.write_text(cleaned)
            data = json.loads(cleaned)
            if isinstance(data, dict) and (data.get('error') or data.get('success') is False or data.get('code', 0) not in (0, '0', None) or data.get('errcode', 0) not in (0, '0', None)):
                failures.append(str(path))
        except (ValueError, OSError):
            pass
    summary = {'status': 'REVIEW_REQUIRED' if result.returncode or failures else 'OUTPUT_READY', 'exitCode': result.returncode,
               'accountId': account['accountId'], 'output': str(folder), 'errorFiles': failures,
               'preview': output[:8000], 'rechargeUrl': account['rechargeUrl']}
    (folder / 'result.json').write_text(json.dumps(summary, indent=2))
    return summary


def export(args):
    rows = json.loads(Path(args.input).read_text())
    for key in args.path.split('.') if args.path else []:
        rows = rows[int(key)] if isinstance(rows, list) else rows[key]
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise Failure('CSV input must select a list of objects.')
    fields = list(dict.fromkeys(k for row in rows for k in row))
    def cell(value):
        value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value if value is not None else '')
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value
    with open(args.output, 'x', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([cell(k) for k in fields])
        writer.writerows([cell(row.get(k)) for k in fields] for row in rows)
    return {'status': 'EXPORTED', 'rows': len(rows), 'file': str(Path(args.output).resolve())}


def main():
    from .capabilities.mock import SCENARIOS
    parser = argparse.ArgumentParser(prog='nexscope')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--api-base', default=None)
    commands = parser.add_subparsers(dest='command', required=True)
    doctor = commands.add_parser('doctor', help='Local diagnostics; no network or stored credential access.')
    doctor.add_argument('--profile', choices=['offline', 'independent', 'plugin'], default='offline')
    doctor.add_argument('--offline', dest='profile', action='store_const', const='offline', help='Alias for --profile offline.')
    doctor.add_argument('--check-output', help='Probe an existing directory with a temporary file, then remove the probe.')
    doctor.add_argument('--json', action='store_true', help='JSON is the default output format.')
    commands.add_parser('get-skills').add_argument('skill', nargs='?', default='core')
    auth_parser = commands.add_parser('auth')
    auth_parser.add_argument('action', choices=['login', 'poll', 'status', 'logout'])
    auth_parser.add_argument('--source-client', choices=['python-cli', 'codex-plugin', 'claude-code'])
    auth_parser.add_argument('--source-channel', choices=['github', 'marketplace', 'local', 'unknown'], default='unknown')
    auth_parser.add_argument('--source-entrypoint', choices=['cli', 'plugin', 'report'], default='cli')
    commands.add_parser('account')
    capabilities = commands.add_parser('capabilities', help='Offline, versioned pilot capability descriptions.')
    describe_capability = capabilities.add_subparsers(dest='capability_action', required=True).add_parser('describe')
    describe_capability.add_argument('capability')
    describe_capability.add_argument('--json', action='store_true', help='JSON is the default output format.')
    data = commands.add_parser('data', help='Plan bounded data requests without network or credentials.')
    data_run = data.add_subparsers(dest='data_action', required=True).add_parser('run')
    data_run.add_argument('capability')
    data_run.add_argument('--input', required=True)
    execution = data_run.add_mutually_exclusive_group(required=True)
    execution.add_argument('--dry-run', action='store_true')
    execution.add_argument('--execute', action='store_true', help='Execute an explicit mock scenario or authorized remote scope.')
    data_run.add_argument('--mock', choices=SCENARIOS)
    data_run.add_argument('--allow-paid', action='store_true', help='Explicitly authorize bounded remote calls; max-calls is not a monetary cap.')
    data_run.add_argument('--out', help='New evidence directory for mock execution.')
    data_run.add_argument('--auth-mode', choices=MODES, default='browser-account')
    data_run.add_argument('--max-calls', type=int, default=3)
    data_run.add_argument('--json', action='store_true', help='JSON is the default output format.')
    workflows = commands.add_parser('workflow', help='Product comparison workflow; remote calls require --execute --allow-paid.')
    workflow = workflows.add_subparsers(dest='workflow_action', required=True).add_parser('compare')
    inputs = workflow.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--asins')
    inputs.add_argument('--keyword')
    inputs.add_argument('--resume', help='Import a completed candidates directory; do not repeat its search.')
    workflow.add_argument('--select-asins')
    workflow.add_argument('--market', help='Defaults to amazon.com, or the saved marketplace with --resume.')
    workflow.add_argument('--auth-mode', choices=MODES, help='Defaults to browser-account, or the saved mode with --resume.')
    workflow.add_argument('--max-calls', type=int, help='Defaults to 4, or the original cumulative budget with --resume.')
    workflow.add_argument('--out', help='New output directory; never overwrite existing evidence.')
    workflow.add_argument('--format', choices=['html', 'csv', 'markdown', 'all'], default='html')
    workflow.add_argument('--mock', choices=SCENARIOS)
    workflow.add_argument('--allow-paid', action='store_true', help='Explicitly authorize bounded remote calls; never retries.')
    workflow.add_argument('--json', action='store_true')
    workflow_execution = workflow.add_mutually_exclusive_group(required=True)
    workflow_execution.add_argument('--dry-run', action='store_true')
    workflow_execution.add_argument('--execute', action='store_true')
    r = commands.add_parser('run')
    r.add_argument('skill'); r.add_argument('--script'); r.add_argument('--output', default='nexscope')
    e = commands.add_parser('export')
    e.add_argument('input'); e.add_argument('--path', default=''); e.add_argument('--output', required=True)
    report = commands.add_parser('report', help='Offline reports from your own data; no account needed.')
    reports = report.add_subparsers(dest='report_action', required=True)
    describe = reports.add_parser('describe', help='Describe input fields, formats and local limits.')
    describe.add_argument('--schema', action='store_true', help='Print the JSON input schema.')
    template = reports.add_parser('template', help='Export a blank standard CSV template.')
    template.add_argument('--format', choices=['csv'], default='csv')
    template.add_argument('--out', required=True)
    demo = reports.add_parser('demo', help='Export fictional sample data (not live market data).')
    demo.add_argument('--format', choices=['csv', 'json'], default='csv')
    demo.add_argument('--out', required=True)
    compare = reports.add_parser('compare', help='Compare a user CSV, JSON array or evidence-backed dataset offline.')
    compare.add_argument('--input', required=True)
    compare.add_argument('--format', choices=['html', 'csv', 'markdown'], default='html')
    compare.add_argument('--out', required=True)
    compare.add_argument('--dry-run', action='store_true', help='Validate and describe outputs without writing.')
    demos = commands.add_parser('demo', help='Run a complete fictional comparison without credentials or network.')
    comparison_demo = demos.add_subparsers(dest='demo_action', required=True).add_parser('product-comparison')
    comparison_demo.add_argument('--out', required=True, help='New output directory.')
    # Split script arguments explicitly so option names cannot change CLI behavior.
    argv = sys.argv[1:]
    tail = argv.index('--') if '--' in argv else len(argv)
    args = parser.parse_args(argv[:tail])
    args.arguments = argv[tail + 1:]
    try:
        if args.command == 'doctor':
            from .doctor import diagnose
            value = diagnose(args.profile, args.check_output, args.api_base)
        elif args.command == 'get-skills': value = guide(args.skill)
        elif args.command == 'export': value = export(args)
        elif args.command == 'report':
            from .reports.compare import command
            value = command(args)
        elif args.command == 'capabilities':
            from .capabilities.catalog import describe
            value = describe(args.capability)
        elif args.command == 'data':
            from .capabilities.plan import command
            value = command(args)
        elif args.command == 'workflow':
            from .workflows.compare import command
            value = command(args)
        elif args.command == 'demo':
            from .capabilities.mock import executor
            from .workflows.compare import compare
            value = compare(executor('browser-account', 'complete', 3), args.out,
                            asins='B000000001,B000000002,B000000003', mock=True, format='all')
        else:
            client = Client(DEFAULT_ORIGIN if args.api_base is None else args.api_base)
            source = None
            if args.command == 'auth' and args.source_client:
                if args.action != 'login':
                    raise Failure('Source options are supported only for auth login.')
                source = {'version': 1, 'client': args.source_client, 'channel': args.source_channel,
                          'campaign': 'cli-data-release', 'entrypoint': args.source_entrypoint}
            value = run(args, client) if args.command == 'run' else client.auth(args.action if args.command == 'auth' else 'status', source)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 1 if value.get('status') in ('REVIEW_REQUIRED', 'UNAVAILABLE', 'PARTIAL', 'FAILED', 'INSUFFICIENT_DATA') else 0
    except DatasetError as e:
        print(json.dumps({'status': 'INVALID_INPUT', 'message': str(e), 'issues': e.issues}))
        return 1
    except (Failure, OSError, ValueError, KeyError) as e:
        print(json.dumps({'status': 'ERROR', 'message': str(e)}))
        return 1
    except Exception as e:
        # Backend/keyring exceptions may embed secret-bearing request details.
        print(json.dumps({'status': 'ERROR', 'message': 'Operation failed (' + type(e).__name__ + '). No automatic retry; check the credential store or saved output.'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
