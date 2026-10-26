# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Origin-bound research HTTP adapter; remote execution requires explicit authorization."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .errors import Failure
from .execution import MAX_RESPONSE_BYTES

ENDPOINTS = ('/api/v1/tools/research/amazon/search', '/api/v1/tools/research/amazon/product/detail')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def decode(raw):
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('Response exceeds the local size bound.')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate response field.')
            result[key] = value
        return result

    def reject(value):
        raise ValueError('Non-finite response value.')

    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=reject)


class HttpTransport:
    cache_namespace = 'research-http.v1'

    def send(self, context, endpoint, body):
        if endpoint not in ENDPOINTS:
            raise Failure('Only registered research endpoints are allowed.')
        request = Request(context.base + endpoint, data=json.dumps(body, allow_nan=False).encode('utf-8'),
                          method='POST', headers={'Authorization': context.authorization(),
                          'Content-Type': 'application/json', 'Accept': 'application/json'})
        try:
            response = build_opener(NoRedirect()).open(request, timeout=30)
        except HTTPError as error:
            # Preserve status even when an error page is HTML, without copying
            # arbitrary error bodies or URLs into evidence or exceptions.
            with error:
                raw = error.read(MAX_RESPONSE_BYTES + 1)
                try:
                    payload = decode(raw)
                except (ValueError, UnicodeError, RecursionError):
                    payload = None
                return error.code, payload
        except (URLError, TimeoutError):
            raise ConnectionError('Network result is uncertain; no retry.') from None
        with response:
            return response.status, decode(response.read(MAX_RESPONSE_BYTES + 1))
