# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Bounded, portable evidence bundles. Hashes detect damage, not authorship."""
import hashlib
import json
from datetime import datetime
import math
from pathlib import Path
import re
import stat

from .errors import Failure

MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_BUNDLE_BYTES = 64 * 1024 * 1024
NAMES = re.compile(r'(?:plan|result|candidates|dataset|search-plan|search-result|report-input|input)\.json|input\.csv|request-[1-4]\.json')


def decode(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key.')
            value[key] = item
        return value

    def reject(value):
        raise ValueError('Non-finite JSON number.')

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite JSON number.')
        return number

    try:
        return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                          parse_constant=reject, parse_float=finite_float)
    except (UnicodeError, ValueError, RecursionError):
        raise Failure('Evidence must be valid UTF-8 JSON without duplicate keys or non-finite numbers.') from None


def bounded_read(path, limit=MAX_FILE_BYTES):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise Failure('Evidence files must be regular files, without links or reparse points.')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise Failure('Evidence exceeds its local size limit.')
    return raw


def read_bundle(folder):
    root = Path(folder)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise Failure('Choose a regular evidence directory, without links or reparse points.')
    manifest = decode(bounded_read(root / 'manifest.json', 65536))
    if (not isinstance(manifest, dict) or manifest.get('schemaVersion') != 'nexscope.evidence.v1'
            or not isinstance(manifest.get('files'), dict) or not 1 <= len(manifest['files']) <= 16):
        raise Failure('Unsupported evidence manifest; use a complete CLI output directory.')
    bundle, total = {}, 0
    for name, digest in manifest['files'].items():
        if not NAMES.fullmatch(name) or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise Failure('Invalid evidence filename or digest.')
        raw = bounded_read(root / name)
        total += len(raw)
        if total > MAX_BUNDLE_BYTES or hashlib.sha256(raw).hexdigest() != digest:
            raise Failure('Evidence size limit or SHA-256 verification failed.')
        bundle[name] = raw
    return bundle


def timestamp(value):
    try:
        return isinstance(value, str) and datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None
    except ValueError:
        return False


def validate_request(value):
    from ..capabilities.plan import plan
    from .auth import MODES, origin
    from .execution import validate_response

    if (not isinstance(value, dict) or value.get('schemaVersion') != 'nexscope.request.v1'
            or type(value.get('sequence')) is not int or not 1 <= value['sequence'] <= 4
            or value.get('authMode') not in MODES or type(value.get('cacheHit')) is not bool
            or value.get('status') not in ('SUCCESS', 'FAILED', 'SKIPPED')
            or value.get('credits') is not None):
        raise Failure('Invalid request evidence structure.')
    origin(value.get('origin'))
    current = plan(value.get('capability'), value.get('params'), auth_mode=value['authMode'], max_calls=4)
    if (len(current['requests']) != 1 or value.get('endpoint') != current['requests'][0]['endpoint']
            or value['params'] != current['requests'][0]['body']
            or value.get('contractVersion') != current['contractVersion'] or value.get('source') != current['source']):
        raise Failure('Request evidence does not match its registered capability contract.')
    if value['status'] == 'SUCCESS':
        error, _ = validate_response(200, value.get('response'), value['capability'], value['params'])
        if error or value.get('error') is not None or not timestamp(value.get('fetchedAt')):
            raise Failure('Invalid successful request evidence.')
    elif (not isinstance(value.get('error'), str) or not re.fullmatch('[A-Z_0-9]+', value['error'])
          or value['cacheHit'] or (value['status'] == 'FAILED' and not timestamp(value.get('fetchedAt')))
          or (value['status'] == 'SKIPPED' and value.get('fetchedAt') is not None)):
        raise Failure('Invalid failed or skipped request evidence.')
    return value


class Artifacts:
    def __init__(self, folder, execution_plan=None):
        self.root = Path(folder).resolve()
        self.root.mkdir(mode=0o700)
        self.files = {}
        if execution_plan is not None:
            self.write('plan.json', execution_plan)

    def write_bytes(self, name, raw):
        if not NAMES.fullmatch(name):
            raise Failure('Invalid evidence filename.')
        with (self.root / name).open('xb') as stream:
            stream.write(raw)
        self.files[name] = hashlib.sha256(raw).hexdigest()

    def write(self, name, value):
        self.write_bytes(name, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode('utf-8'))

    def record(self, result):
        self.write('request-' + str(result['sequence']) + '.json', result)

    def finish(self):
        with (self.root / 'manifest.json').open('x', encoding='utf-8') as stream:
            json.dump({'schemaVersion': 'nexscope.evidence.v1', 'files': self.files}, stream, indent=2)
