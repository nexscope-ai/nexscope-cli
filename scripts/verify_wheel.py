"""Install and verify a wheel outside its checkout; no real service calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid
import venv
import zipfile


def run(command, *, cwd, environment):
    completed = subprocess.run(list(map(str, command)), cwd=cwd, env=environment,
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
    return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    parser.add_argument('--previous-wheel', type=Path)
    parser.add_argument('--with-dependencies', action='store_true', help='Install reviewed hash-pinned online dependencies, then test the legacy browser runner with loopback fixtures.')
    parser.add_argument('--with-os-keyring', action='store_true', help='Check a unique fictional credential in the real OS store, including rollback and uninstall persistence.')
    parser.add_argument('--pip-wheel', type=Path, help='Explicit reviewed pip wheel to bootstrap a venv when the host lacks ensurepip; never installs into the system interpreter.')
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    previous = args.previous_wheel.resolve(strict=True) if args.previous_wheel else None
    pip_wheel = args.pip_wheel.resolve(strict=True) if args.pip_wheel else None
    if args.with_os_keyring and not args.with_dependencies:
        parser.error('--with-os-keyring requires --with-dependencies')
    root = Path(__file__).resolve().parents[1]
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith(('PYTHON', 'NEXSCOPE_', 'PIP_'))}
    environment.update(PYTHONUTF8='1', PYTHONNOUSERSITE='1', PIP_CONFIG_FILE=os.devnull,
                       PIP_DISABLE_PIP_VERSION_CHECK='1')
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        required = {'nexscope_cli/core/evidence.py', 'nexscope_cli/core/auth.py',
                    'nexscope_cli/capabilities/plan.py', 'nexscope_cli/reports/compare.py',
                    'nexscope_cli/workflows/compare.py', 'nexscope_cli/compat/legacy.py',
                    'nexscope_cli/catalog.json', 'nexscope_cli/api-contract.json',
                    'nexscope_cli/dependency-lock.json', 'nexscope_cli/dependencies.lock',
                    'nexscope_cli/tools.json', 'nexscope_cli/tools.py', 'nexscope_cli/core/mcp.py'}
        required.update('nexscope_cli/resources/' + name for name in
                        ['fields.json', 'products.schema.json', 'products-template.csv',
                         'products-sample.csv', 'products-sample.json', 'report.html', 'mock-products.json'])
        for name, script in [('amazon-search', 'amazon_search.py'), ('amazon-product-detail', 'amazon_product_detail.py')]:
            required.update('nexscope_cli/skills/' + name + '/' + item for item in
                            ['SKILL.md', 'requirements.txt', 'references/api.md', 'scripts/' + script])
        assert required <= names, sorted(required - names)
        assert any(name.endswith('.dist-info/licenses/LICENSE') for name in names)
        assert any(name.endswith('.dist-info/licenses/NOTICE') for name in names)
        assert not any('__pycache__' in name or name.endswith('.pyc') for name in names)
    with tempfile.TemporaryDirectory(prefix='nexscope-wheel-') as temporary:
        work = Path(temporary)
        assert not work.resolve().is_relative_to(root)
        target = work / 'environment'
        # Match `python -m venv`: copied macOS interpreters can lose libpython's relative path.
        venv.EnvBuilder(with_pip=pip_wheel is None, symlinks=os.name != 'nt').create(target)
        python = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        entry = target / ('Scripts/nexscope.exe' if os.name == 'nt' else 'bin/nexscope')
        install = [python, '-I', '-m', 'pip', 'install', '--no-index', '--no-deps', '--force-reinstall']
        command = work / 'command'
        command.mkdir()
        if pip_wheel:
            bootstrap = "import sys; sys.path.insert(0, sys.argv[1]); from pip._internal.cli.main import main; sys.exit(main(['install','--no-index','--no-deps',sys.argv[1]]))"
            run([python, '-I', '-c', bootstrap, pip_wheel], cwd=command, environment=environment)
        report = command / 'user-report.txt'
        report.write_text('report survives upgrades and rollback', encoding='utf-8')
        sentinel_env = dict(environment, NEXSCOPE_API_KEY='fixture-sentinel')
        if previous:
            run([*install, previous], cwd=command, environment=environment)
        run([*install, wheel], cwd=command, environment=environment)
        if args.with_dependencies:
            run([python, '-I', '-m', 'pip', 'install', '--require-hashes', '--index-url', 'https://pypi.org/simple',
                 '-r', root / 'cli' / 'nexscope_cli' / 'dependencies.lock'], cwd=command, environment=environment)
        version = run([entry, '--version'], cwd=command, environment=sentinel_env).stdout.strip()
        shutil.copytree(root / 'tests', command / 'tests', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copyfile(root / 'scripts' / 'installed_checks.py', command / 'installed_checks.py')
        checks = run([python, '-I', command / 'installed_checks.py'], cwd=command, environment=environment)
        print(checks.stderr, end='')
        summary = json.loads(checks.stdout)
        if args.with_dependencies:
            online_work = work / 'with-dependencies'
            online_work.mkdir()
            online = run([python, '-I', command / 'installed_checks.py', '--loopback-only', '--with-dependencies'],
                         cwd=online_work, environment=environment)
            summary['legacyBrowserRunner'] = json.loads(online.stdout)['status']
        keyring_origin = 'https://nexscope-acceptance-' + uuid.uuid4().hex + '.invalid'
        keyring_result = None
        keyring_script = command / 'verify_os_keyring.py'
        shutil.copyfile(root / 'scripts' / 'verify_os_keyring.py', keyring_script)
        if args.with_dependencies:
            summary['osKeyringPrerequisite'] = json.loads(run([python, '-I', keyring_script, 'probe', keyring_origin],
                                                             cwd=command, environment=environment).stdout)
        try:
            if args.with_os_keyring:
                keyring_result = json.loads(run([python, '-I', keyring_script, 'write', keyring_origin],
                                                cwd=command, environment=environment).stdout)
                summary['osKeyring'] = {'backend': keyring_result['backend'], 'writeRead': 'PASSED'}
            if previous:
                run([*install, previous], cwd=command, environment=environment)
                old_version = run([entry, '--version'], cwd=command, environment=sentinel_env).stdout.strip()
                assert old_version != version, 'Rollback wheel must have a different version'
                if keyring_result:
                    run([python, '-I', keyring_script, 'read', keyring_origin, '--digest', keyring_result['digest']],
                        cwd=command, environment=environment)
                    summary['osKeyring']['rollbackPersistence'] = 'PASSED'
                run([*install, wheel], cwd=command, environment=environment)
                assert run([entry, '--version'], cwd=command, environment=sentinel_env).stdout.strip() == version
                summary['upgradeRollback'] = {'previousVersion': old_version, 'restoredVersion': version, 'status': 'PASSED'}
            if keyring_result:
                run([python, '-I', keyring_script, 'read', keyring_origin, '--digest', keyring_result['digest']],
                    cwd=command, environment=environment)
                summary['osKeyring']['upgradePersistence'] = 'PASSED'
                run([python, '-I', '-m', 'pip', 'uninstall', '-y', 'nexscope-cli'], cwd=command, environment=environment)
                run([python, '-I', keyring_script, 'read', keyring_origin, '--digest', keyring_result['digest']],
                    cwd=command, environment=environment)
                summary['osKeyring']['uninstallPersistence'] = 'PASSED'
                run([*install, wheel], cwd=command, environment=environment)
        finally:
            if keyring_result:
                run([python, '-I', keyring_script, 'delete', keyring_origin, '--digest', keyring_result['digest']],
                    cwd=command, environment=environment)
                summary['osKeyring']['cleanup'] = 'PASSED'
        assert report.read_text() == 'report survives upgrades and rollback'
        assert sentinel_env['NEXSCOPE_API_KEY'] == 'fixture-sentinel'
        summary.update(wheel=wheel.name, sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
                       wheelEntries=len(names), sourcePathInjection='REMOVED', outsideCheckout=True,
                       dependenciesInstalled=args.with_dependencies)
        if pip_wheel:
            summary['pipBootstrap'] = {'wheel': pip_wheel.name, 'sha256': hashlib.sha256(pip_wheel.read_bytes()).hexdigest()}
        print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
