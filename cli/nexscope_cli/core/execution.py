# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Bounded execution with injected transport and session-only success caching."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import time

from .errors import Failure
from ..capabilities.catalog import describe
from ..capabilities.plan import plan

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def redact(value, context):
    if isinstance(value, str):
        return context.redact(value)
    if isinstance(value, list):
        return [redact(item, context) for item in value]
    if isinstance(value, dict):
        return {context.redact(str(key)): redact(item, context) for key, item in value.items()}
    return value


class SessionCache:
    """Never persists credentials, identities or responses across processes."""
    def __init__(self, ttl=300, clock=time.time):
        if type(ttl) not in (int, float) or not 0 < ttl <= 86400:
            raise Failure('Cache TTL must be greater than zero and at most 86400 seconds.')
        self.ttl, self.clock, self.entries = ttl, clock, {}

    def get(self, key):
        entry = self.entries.get(key)
        if entry is None:
            return None
        age = self.clock() - entry['created']
        if age < 0 or age >= self.ttl:
            self.entries.pop(key, None)
            return None
        return deepcopy(entry['value'])

    def put(self, key, value):
        self.entries[key] = {'created': self.clock(), 'value': deepcopy(value)}

    def invalidate(self, partition):
        self.entries = {key: value for key, value in self.entries.items() if key[0] != partition}


def validate_response(status, payload, capability, body):
    """Strict documented envelope; live sample verification remains a separate acceptance gate."""
    if type(status) is not int or not 100 <= status <= 599:
        return 'INVALID_HTTP_STATUS', False
    if status != 200:
        return 'HTTP_' + str(status), status in (401, 402, 403, 429)
    if not isinstance(payload, dict) or type(payload.get('code')) is not int:
        return 'INVALID_ENVELOPE', False
    if payload['code'] != 0:
        return 'BUSINESS_' + str(payload['code']), payload['code'] in (12001, 12003, 13011)
    data = payload.get('data')
    if not isinstance(data, dict) or not isinstance(data.get('products'), list):
        return 'INVALID_DATA', False
    products = data['products']
    if not products:
        return 'EMPTY_DATA', False
    seen = set()
    for row in products:
        if not isinstance(row, dict) or not isinstance(row.get('asin'), str) or not row['asin'] or not isinstance(row.get('title'), str) or not row['title'].strip():
            return 'INVALID_PRODUCT', False
        if row['asin'] in seen:
            return 'DUPLICATE_PRODUCT', False
        seen.add(row['asin'])
        for field in ('extractedPrice', 'price', 'rating', 'ratingScale', 'reviews', 'ratings'):
            value = row.get(field)
            if value is not None:
                try:
                    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                        return 'INVALID_PRODUCT', False
                except OverflowError:
                    return 'INVALID_PRODUCT', False
        if row.get('ratingScale') is not None and row['ratingScale'] <= 0:
            return 'INVALID_PRODUCT', False
        if row.get('rating') is not None and row.get('ratingScale') is not None and row['rating'] > row['ratingScale']:
            return 'INVALID_PRODUCT', False
        if any(row.get(f) is not None and int(row[f]) != row[f] for f in ('reviews', 'ratings')):
            return 'INVALID_PRODUCT', False
        currency = row.get('currency')
        if currency is not None and not isinstance(currency, str):
            return 'INVALID_PRODUCT', False
    if capability == 'amazon-product-detail' and (len(products) != 1 or products[0]['asin'] != body['asins']):
        return 'MISMATCHED_PRODUCT', False
    return None, False


class Executor:
    """One explicit context and one shared request budget across workflow steps.

    The transport receives (context, endpoint, body), returning (http_status,
    parsed_json). Remote transport is explicitly gated; mock transports use no credentials.
    """
    def __init__(self, context, transport, *, max_calls=3, cache=None, clock=time.time, record=None):
        if type(max_calls) is not int or max_calls < 1:
            raise Failure('max-calls must be a positive integer.')
        self.context, self.transport = context, transport
        self.max_calls, self.clock = max_calls, clock
        self.cache = cache if cache is not None else SessionCache(clock=clock)
        self.sent, self.results, self.stopped = 0, [], False
        self.imported_results = []
        self.record = record

    def execute(self, capability, params):
        # Rebuild from validated input, never trust a serialized plan to execute.
        current = plan(capability, params, auth_mode=self.context.mode, max_calls=self.max_calls)
        description = describe(capability)
        batch = []
        for request in current['requests']:
            body = request['body']
            result = {'schemaVersion': 'nexscope.request.v1',
                      'sequence': len(self.imported_results) + len(self.results) + 1, 'capability': capability,
                      'origin': self.context.base, 'authMode': self.context.mode,
                      'contractVersion': description['contractVersion'], 'source': description['source'],
                      'endpoint': request['endpoint'], 'params': redact(body, self.context),
                      'cacheHit': False, 'fetchedAt': None, 'status': 'SKIPPED',
                      'error': None, 'response': None, 'credits': None}
            key = (self.context.cache_partition, self.transport.cache_namespace,
                   capability, description['contractVersion'], description['source']['sha256'],
                   json.dumps(body, sort_keys=True, separators=(',', ':')))
            if self.stopped:
                result['error'] = 'STOPPED_AFTER_FAILURE'
            else:
                cached = self.cache.get(key)
                if cached is not None:
                    result.update(cached, cacheHit=True, status='SUCCESS')
                elif self.sent + len(self.imported_results) >= self.max_calls:
                    result['error'] = 'CALL_BUDGET_EXHAUSTED'
                else:
                    # An ambiguous failed call still consumes the local budget.
                    self.sent += 1
                    result['fetchedAt'] = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat()
                    try:
                        http_status, raw = self.transport.send(self.context, request['endpoint'], deepcopy(body))
                        encoded = json.dumps(raw, allow_nan=False).encode('utf-8')
                        if len(encoded) > MAX_RESPONSE_BYTES:
                            raise ValueError
                        error, stop = validate_response(http_status, raw, capability, body)
                        result.update(status='FAILED' if error else 'SUCCESS', error=error,
                                      response=redact(raw, self.context))
                        self.stopped = stop
                        if stop:
                            self.cache.invalidate(self.context.cache_partition)
                    except (TimeoutError, ConnectionError, OSError):
                        result.update(status='FAILED', error='NETWORK_UNCERTAIN')
                        self.stopped = True
                    except (TypeError, ValueError, RecursionError):
                        result.update(status='FAILED', error='INVALID_RESPONSE')
                    if result['status'] == 'SUCCESS':
                        self.cache.put(key, {'response': result['response'], 'fetchedAt': result['fetchedAt']})
            if self.record is not None:
                self.record(deepcopy(result))
            self.results.append(deepcopy(result))
            batch.append(result)
        return batch

    def summary(self):
        return {'maxCalls': self.max_calls, 'requestsSent': self.sent + len(self.imported_results),
                'requestsSentThisRun': self.sent, 'importedRequests': len(self.imported_results),
                'cacheHits': sum(r['cacheHit'] for r in self.results),
                'automaticRetries': 0, 'estimatedCredits': None, 'billingCap': None,
                'pricingStatus': 'UNKNOWN', 'cachePolicy': 'memory-only-session-ttl',
                'stoppedAfterFailure': self.stopped}
