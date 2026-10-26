# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Deterministic, explicitly fictional fixtures. Never imports a network client."""
from copy import deepcopy
from importlib.resources import files
import json

from ..core.auth import AuthContext
from ..core.errors import Failure
from ..core.execution import Executor

SCENARIOS = ('complete', 'partial', 'empty', 'unauthorized', 'credits', 'rate-limit', 'timeout', 'malformed')


class MockTransport:
    def __init__(self, scenario='complete'):
        if scenario not in SCENARIOS:
            raise Failure('Unknown mock scenario.')
        self.scenario, self.calls = scenario, []
        self.cache_namespace = 'fictional-v1:' + scenario
        self.fixture = json.loads(files('nexscope_cli.resources').joinpath('mock-products.json').read_text(encoding='utf-8'))

    def send(self, context, endpoint, body):
        self.calls.append((endpoint, deepcopy(body)))
        if self.scenario == 'timeout':
            raise TimeoutError('Fixture timeout')
        if self.scenario == 'unauthorized':
            return 401, {'code': 12003, 'data': None}
        if self.scenario == 'credits':
            return 200, {'code': 13011, 'data': None}
        if self.scenario == 'rate-limit':
            return 429, {'code': 429, 'data': None}
        if self.scenario == 'malformed':
            return 200, {'code': '0', 'data': None}
        if self.scenario == 'empty':
            return 200, {'code': 0, 'data': {'products': []}}
        rows = deepcopy(self.fixture['products'])
        if endpoint.endswith('/product/detail'):
            if self.scenario == 'partial' and body['asins'] == 'B000000002':
                return 200, {'code': 0, 'data': {'products': []}}
            index = sum(map(ord, body['asins'])) % len(rows)
            row = next((row for row in rows if row['asin'] == body['asins']), rows[index])
            row['asin'] = body['asins']
            row['link'] = 'https://example.invalid/product/' + body['asins']
            rows = [row]
        return 200, {'code': 0, 'msg': None, 'data': {'products': rows}, 'cost': '12'}


def executor(mode, scenario, max_calls):
    # Fake credentials are generated internally; inherited keys and keyring are
    # deliberately not accessed, even when the requested mode is browser-account.
    context = AuthContext(mode, 'https://mock.invalid', 'fictional-context-only')
    return Executor(context, MockTransport(scenario), max_calls=max_calls)
