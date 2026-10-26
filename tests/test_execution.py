import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from nexscope_cli.capabilities.mock import MockTransport, executor
from nexscope_cli.compat.legacy import LegacySession
from nexscope_cli.core.auth import AuthContext, origin, resolve_auth
from nexscope_cli.core.errors import AuthRequired, Failure
from nexscope_cli.core.execution import Executor, SessionCache
from nexscope_cli.core.transport import HttpTransport, decode


class ExecutionTests(unittest.TestCase):
    def test_auth_sources_never_fall_back_or_read_the_other_source(self):
        environment = {'NEXSCOPE_API_KEY': 'env-fixture', 'NEXSCOPE_PROXY_BASE': 'https://env.invalid'}
        browser = resolve_auth('browser-account', environment=environment, credential_loader=lambda: {'apiKey': 'browser-fixture'})
        self.assertEqual(browser.authorization(), 'Bearer browser-fixture')
        independent = resolve_auth('env-api-key', environment=environment, credential_loader=lambda: self.fail('Read browser credentials'))
        self.assertEqual(independent.authorization(), 'Bearer env-fixture')
        with self.assertRaises(AuthRequired):
            resolve_auth('browser-account', environment=environment, credential_loader=lambda: None)
        with self.assertRaises(AuthRequired):
            resolve_auth('env-api-key', environment={}, credential_loader=lambda: {'apiKey': 'browser-fixture'})
        self.assertNotIn('browser-fixture', repr(browser))
        self.assertEqual(browser.redact('key=browser-fixture'), 'key=[REDACTED]')

    def test_shared_cache_is_partitioned_by_context_mode_origin_and_params(self):
        cache = SessionCache()
        transport = MockTransport()
        contexts = [AuthContext('browser-account', 'https://a.invalid', 'one'),
                    AuthContext('browser-account', 'https://a.invalid', 'two'),
                    AuthContext('env-api-key', 'https://a.invalid', 'one'),
                    AuthContext('env-api-key', 'https://b.invalid', 'one')]
        params = {'keyword': 'lamp', 'amazonDomain': 'amazon.com'}
        for context in contexts:
            engine = Executor(context, transport, cache=cache)
            first = engine.execute('amazon-search', params)[0]
            second = engine.execute('amazon-search', params)[0]
            self.assertFalse(first['cacheHit'])
            self.assertTrue(second['cacheHit'])
            self.assertEqual(first['fetchedAt'], second['fetchedAt'])
            engine.execute('amazon-search', dict(params, amazonDomain='amazon.de'))
        self.assertEqual(len(transport.calls), 8)
        self.assertNotIn('one', repr(cache.entries.keys()))

    def test_expired_or_invalid_responses_never_count_as_success_cache(self):
        now = [1000]
        cache = SessionCache(ttl=5, clock=lambda: now[0])
        engine = Executor(AuthContext('browser-account', 'https://a.invalid', 'fake'), MockTransport(), cache=cache, clock=lambda: now[0])
        params = {'keyword': 'lamp'}
        first = engine.execute('amazon-search', params)[0]
        now[0] += 5
        second = engine.execute('amazon-search', params)[0]
        self.assertFalse(second['cacheHit'])
        self.assertNotEqual(first['fetchedAt'], second['fetchedAt'])
        for scenario in ['empty', 'malformed']:
            failed = executor('env-api-key', scenario, 3)
            failed.execute('amazon-search', params)
            failed.execute('amazon-search', params)
            self.assertEqual(len(failed.transport.calls), 2)
            self.assertFalse(failed.cache.entries)

    def test_budget_and_terminal_failures_stop_without_retry(self):
        for scenario in ['unauthorized', 'credits', 'rate-limit', 'timeout']:
            with self.subTest(scenario=scenario):
                engine = executor('browser-account', scenario, 3)
                rows = engine.execute('amazon-product-detail', {'asins': 'A,B,C'})
                self.assertEqual([row['status'] for row in rows], ['FAILED', 'SKIPPED', 'SKIPPED'])
                self.assertEqual(engine.sent, 1)
                self.assertEqual(len(engine.transport.calls), 1)
                self.assertEqual(engine.summary()['automaticRetries'], 0)
        engine = executor('env-api-key', 'complete', 2)
        engine.execute('amazon-search', {'keyword': 'lamp'})
        rows = engine.execute('amazon-product-detail', {'asins': 'A,B'})
        self.assertEqual(rows[-1]['error'], 'CALL_BUDGET_EXHAUSTED')
        self.assertEqual(engine.sent, 2)

    def test_credentials_are_redacted_from_response_evidence(self):
        engine = executor('env-api-key', 'complete', 3)
        engine.transport.fixture['products'][0]['title'] = 'fictional-context-only'
        results = engine.execute('amazon-search', {'keyword': 'lamp'})
        self.assertNotIn('fictional-context-only', json.dumps(results))
        self.assertIn('[REDACTED]', json.dumps(results))

    def test_origin_and_transport_reject_unregistered_routes_and_redirects(self):
        for value in ['http://external.invalid', 'https://user:pass@example.invalid',
                      'https://example.invalid/path', 'https://example.invalid/?key=x',
                      'https://example.invalid:bad', 'https://example.invalid/#secret']:
            with self.subTest(value=value), self.assertRaises(Failure):
                origin(value)
        context = AuthContext('env-api-key', 'http://127.0.0.1:1234', 'fixture')
        with self.assertRaises(Failure):
            HttpTransport().send(context, '/unregistered', {})
        error = HTTPError(context.base, 302, 'Redirect', {}, None)
        with patch('nexscope_cli.core.transport.build_opener') as opener:
            opener.return_value.open.side_effect = error
            status, payload = HttpTransport().send(context, '/api/v1/tools/research/amazon/search', {'keyword': 'lamp'})
        self.assertEqual(status, 302)
        self.assertIsNone(payload)
        for raw in [b'{"code":0,"code":1}', b'{"x":NaN}']:
            with self.assertRaises(ValueError):
                decode(raw)

    def test_legacy_batch_and_page_are_forwarded_unchanged_once(self):
        context = AuthContext('env-api-key', 'https://fixture.invalid', 'legacy-fixture')
        transport = MockTransport()
        session = LegacySession(context, transport)
        search = {'keyword': 'lamp', 'page': 8, 'customLegacyFlag': True}
        detail = {'asins': 'A,B,C,D', 'returnRelatedProducts': True}
        session.call('amazon-search', search, use_cache=False)
        session.call('amazon-product-detail', detail, use_cache=False)
        self.assertEqual([call[1] for call in transport.calls], [search, detail])
        with self.assertRaises(Failure):
            LegacySession(AuthContext('browser-account', 'https://fixture.invalid', 'fake'))


if __name__ == '__main__':
    unittest.main()
