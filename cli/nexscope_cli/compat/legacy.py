# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Preserve standalone JSON/flags/environment access without pilot scope limits."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time

from ..core.auth import resolve_auth
from ..core.errors import Failure
from ..core.execution import SessionCache, redact, validate_response
from ..core.transport import HttpTransport

CAPABILITIES = {
    'amazon-search': ('/api/v1/tools/research/amazon/search', 'ecommerce.amazon-search-amazon_search'),
    'amazon-product-detail': ('/api/v1/tools/research/amazon/product/detail', 'ecommerce.amazon-product-detail-amazon_product_detail'),
}


class LegacySession:
    """A new session snapshots the explicitly selected environment credentials.

    The legacy input object is sent once, unchanged. Do not apply the pilot's
    one-page/three-ASIN planner, split batches, or add default request fields.
    """
    def __init__(self, context, transport=None, cache=None):
        if context.mode != 'env-api-key':
            raise Failure('Independent Skills require an explicit env-api-key context.')
        self.context = context
        self.transport = transport if transport is not None else HttpTransport()
        self.cache = cache if cache is not None else SessionCache()

    def call(self, capability, params, use_cache=True):
        if capability not in CAPABILITIES or not isinstance(params, dict):
            raise Failure('Use a registered legacy Skill and a JSON object.')
        canonical = json.dumps(params, sort_keys=True, allow_nan=False)
        key = (self.context.cache_partition, self.transport.cache_namespace,
               'legacy-envelope.v1', capability, canonical)
        cached = self.cache.get(key) if use_cache else None
        if cached is not None:
            payload = cached['payload']
            metadata = payload.get('_cache')
            payload['_cache'] = {**(metadata if isinstance(metadata, dict) else {}), 'hit': True,
                                 'fetchedAt': cached['fetchedAt']}
            return payload
        status, payload = self.transport.send(self.context, CAPABILITIES[capability][0], params)
        if not isinstance(payload, dict):
            payload = {'error': 'HTTP ' + str(status) + ': response is not a JSON object'}
        payload = redact(payload, self.context)
        # Cache only the response subset already validated by the common core.
        # Use the common envelope/product checks, not the pilot detail check
        # (which assumes a single ASIN and would reject legacy batches).
        # Unknown valid server shapes are still returned unchanged, never guessed.
        error, stop = validate_response(status, payload, 'amazon-search', params)
        if stop:
            self.cache.invalidate(self.context.cache_partition)
        if use_cache and error is None:
            self.cache.put(key, {'payload': payload,
                                'fetchedAt': datetime.fromtimestamp(self.cache.clock(), timezone.utc).isoformat()})
        return payload


def largest_list(value, prefix=''):
    if isinstance(value, list):
        return prefix, len(value), value
    best = (None, -1, None)
    if isinstance(value, dict):
        for key, child in value.items():
            found = largest_list(child, prefix + '.' + key if prefix else key)
            if found[1] > best[1]:
                best = found
    return best


def summarize(result):
    print('Top-level keys: ' + str(list(result)))
    for key in ('errcode', 'code', 'errmsg', 'msg', 'total', 'count', 'costToken', 'costTime'):
        if isinstance(result.get(key), (int, float, bool, str)):
            print('  ' + key + ': ' + str(result[key]))
    path, count, rows = largest_list(result)
    if path and rows:
        print('\nLongest list: `' + path + '` (' + str(count) + ' items)')
        print('First ' + str(min(3, count)) + ':')
        print(json.dumps(rows[:3], ensure_ascii=False, indent=2))


def output_path(capability):
    moment = datetime.now()
    session = os.environ.get('SESSION_ID', '').strip() or moment.strftime('%H%M%S')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', session):
        raise Failure('SESSION_ID must be a safe directory name (letters, digits, dot, underscore, dash).')
    root = Path.cwd().resolve()
    folder = root / 'nexscope' / moment.strftime('%Y-%m-%d') / session / 'data'
    if not folder.resolve().is_relative_to(root):
        raise Failure('Output must remain inside the working directory.')
    folder.mkdir(parents=True, exist_ok=True)
    if not folder.resolve().is_relative_to(root):
        raise Failure('Output must remain inside the working directory.')
    return folder / (CAPABILITIES[capability][1] + '-' + str(time.time_ns() // 1000) + '.json')


def main(capability, argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    options = [arg for arg in args if arg not in ('--inline', '--no-cache')]
    if len(options) != 1:
        print("Usage: python script.py '<JSON params>' [--inline] [--no-cache]", file=sys.stderr)
        return 1
    target = None
    created = False
    try:
        def reject(value):
            raise ValueError('Non-finite JSON values are not supported.')
        params = json.loads(options[0], parse_constant=reject)
        if not isinstance(params, dict) or capability not in CAPABILITIES:
            raise Failure('Params must be a JSON object for a registered Skill.')
        context = resolve_auth('env-api-key')
        target = output_path(capability)
        # Reserve output before requesting data; never fall back to home or temp.
        with target.open('x', encoding='utf-8') as stream:
            created = True
            session = LegacySession(context)
            result = session.call(capability, params, use_cache='--no-cache' not in args)
            serialized = json.dumps(result, ensure_ascii=False, allow_nan=False)
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print('Saved full response: ' + str(target) + ' (' + str(len(serialized)) + ' bytes)')
        if isinstance(result.get('_cache'), dict) and result['_cache'].get('hit'):
            print('Cache hit')
        if '--inline' in args or len(serialized.encode('utf-8')) <= 8000:
            print(serialized)
        else:
            summarize(result)
        # Retain legacy behavior: JSON business errors are output, not rewrapped.
        # Callers must inspect outer code/error, not infer success from exit zero.
        return 0
    except Exception as error:
        if created and target is not None and target.exists() and target.stat().st_size == 0:
            target.unlink()
        message = str(error) if isinstance(error, Failure) else 'Operation failed (' + type(error).__name__ + '); no automatic retry.'
        print(message, file=sys.stderr)
        return 1
