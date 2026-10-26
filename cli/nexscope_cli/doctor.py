# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Local diagnostics. Never connect, initialize a keyring or read stored credentials."""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

from . import __version__
from .core.auth import DEFAULT_ORIGIN, origin
from .core.errors import Failure

PROFILES = ('offline', 'independent', 'plugin')
DEPENDENCIES = {'keyring': (25, 26), 'requests': (2, 3), 'jmespath': (1, 2),
                'qrcode': (8, 9), 'oss2': (2, 3)}
MINIMUMS = {'keyring': (25,), 'requests': (2, 32), 'jmespath': (1,),
            'qrcode': (8,), 'oss2': (2, 19)}


def dependency_names():
    profile = json.loads(Path(__file__).with_name('catalog.json').read_text(encoding='utf-8')).get('distributionProfile', 'full')
    if profile not in ('data-only', 'full'):
        raise ValueError('Unknown distribution profile.')
    return ('keyring', 'requests') if profile == 'data-only' else tuple(DEPENDENCIES)


def resources(root):
    """Check installed bytes, including the resources needed for free reports."""
    catalog = json.loads((root / 'catalog.json').read_text(encoding='utf-8'))
    count = 0
    for name, entry in catalog['skills'].items():
        for relative, digest in entry['files'].items():
            file = (root / 'skills' / name / relative).resolve()
            if not file.is_relative_to((root / 'skills').resolve()):
                raise ValueError('Invalid resource path')
            if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                raise ValueError('Resource digest mismatch')
            count += 1
    for name in ('fields.json', 'products.schema.json', 'products-template.csv',
                 'products-sample.csv', 'products-sample.json', 'report.html', 'mock-products.json'):
        data = (root / 'resources' / name).read_bytes()
        if not data:
            raise ValueError('Empty report resource')
        if name.endswith('.json'):
            json.loads(data)
    return count


def diagnose(profile='offline', output_dir=None, api_base=None):
    if profile not in PROFILES:
        raise ValueError('Unknown diagnostic profile.')
    checks = []

    def check(name, status, detail, action=None):
        checks.append({'name': name, 'status': status, 'detail': detail, 'action': action})

    check('python', 'PASS' if sys.version_info >= (3, 11) else 'FAIL', '.'.join(map(str, sys.version_info[:3])),
          'Use Python 3.11 or newer.' if sys.version_info < (3, 11) else None)
    try:
        installed = metadata.version('nexscope-cli')
        check('package-version', 'PASS' if installed == __version__ else 'FAIL',
              'Installed metadata matches loaded code.' if installed == __version__ else 'Installed metadata differs from loaded code.',
              None if installed == __version__ else 'Reinstall the paired wheel in this Python environment.')
    except metadata.PackageNotFoundError:
        check('package-version', 'WARN', 'No installed distribution metadata.', 'Install the paired wheel before installation acceptance.')
    try:
        count = resources(Path(__file__).parent)
        check('resources', 'PASS', {'hashedSkillFiles': count, 'reportResources': 7})
    except Exception:
        check('resources', 'FAIL', 'Required resources are missing, invalid or have a digest mismatch.', 'Reinstall the verified wheel; do not disable integrity checks.')
    if profile == 'plugin':
        for name in dependency_names():
            _, upper = DEPENDENCIES[name]
            try:
                raw = metadata.version(name)
                # No dependency import: importing keyring can initialize user configuration.
                match = re.fullmatch(r'\d+(?:\.\d+)*', raw)
                version = tuple(map(int, raw.split('.'))) if match else ()
                valid = bool(version) and MINIMUMS[name] <= version < (upper,)
                check('dependency:' + name, 'PASS' if valid else 'FAIL', 'Compatible version installed.' if valid else 'Version outside the supported stable range.',
                      None if valid else 'Install the hash-pinned dependency profile paired with this wheel.')
            except metadata.PackageNotFoundError:
                check('dependency:' + name, 'FAIL', 'Dependency is not installed.', 'Install the hash-pinned dependency profile paired with this wheel.')
        check('uv', 'PASS' if shutil.which('uv') else 'WARN',
              'Installer found on PATH.' if shutil.which('uv') else 'Optional installer not found on PATH.',
              'Use the documented installer before plugin setup; no installer is run by doctor.')
        check('credential-store', 'NOT_CHECKED', 'No keyring initialization, access or credential validation.',
              'Validate the OS credential store separately in an authorized connection test.')
        try:
            origin(api_base if api_base is not None else DEFAULT_ORIGIN)
            check('api-origin', 'PASS', 'Origin syntax accepted; reachability not tested.')
        except Failure:
            check('api-origin', 'FAIL', 'Invalid API origin.', 'Use an HTTPS origin without credentials, path, query or fragment.')
    elif profile == 'independent':
        key = os.environ.get('NEXSCOPE_API_KEY', '').strip()
        base = os.environ.get('NEXSCOPE_PROXY_BASE', '').strip()
        valid_key = bool(key) and not any(c.isspace() or ord(c) < 32 for c in key)
        check('environment-key', 'PASS' if valid_key else 'FAIL',
              'Key is configured; server validity not tested.' if valid_key else 'Key is missing or malformed.',
              None if valid_key else 'Configure NEXSCOPE_API_KEY privately; never paste it into diagnostic output.')
        try:
            if api_base is not None:
                raise Failure('Independent mode uses its environment origin.')
            origin(base)
            check('environment-origin', 'PASS', 'Origin syntax accepted; value omitted.')
        except Failure:
            check('environment-origin', 'FAIL', 'Environment origin missing/invalid or --api-base supplied.',
                  'Configure NEXSCOPE_PROXY_BASE as an HTTPS origin; omit --api-base.')
    if output_dir is not None:
        try:
            folder = Path(output_dir)
            if not folder.is_dir():
                raise OSError('Directory must already exist.')
            with tempfile.TemporaryDirectory(prefix='.nexscope-doctor-', dir=folder) as probe:
                target = Path(probe) / 'probe'
                target.write_bytes(b'nexscope-doctor')
                if target.read_bytes() != b'nexscope-doctor':
                    raise OSError('Readback mismatch.')
            check('output-directory', 'PASS', 'Created, read and removed only a temporary probe directory.')
        except Exception:
            check('output-directory', 'FAIL', 'Output directory probe failed; path and exception details omitted.',
                  'Choose an existing writable directory; check disk space and path length.')
    else:
        check('output-directory', 'NOT_CHECKED', 'No files written.', 'Optionally pass --check-output with an existing directory.')
    failed = any(c['status'] == 'FAIL' for c in checks)
    warnings = any(c['status'] == 'WARN' for c in checks)
    return {'schemaVersion': 1, 'status': 'FAILED' if failed else 'WARNING' if warnings else 'READY_LOCAL',
            'version': __version__, 'profile': profile, 'os': sys.platform, 'checks': checks,
            'network': 'NOT_RUN', 'storedCredentials': 'NOT_READ', 'telemetry': 'NONE',
            'environmentValues': 'syntax checked without output' if profile == 'independent' else 'NOT_READ',
            'scope': 'Local prerequisites only; not authenticated, live-service or assistant-host acceptance.'}
