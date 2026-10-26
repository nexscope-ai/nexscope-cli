# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Origin-bound MCP HTTP sessions. Never retry a tool invocation."""
import json
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from .errors import Failure
from .evidence import decode
from .transport import NoRedirect
from .attribution import headers as client_headers

ENDPOINT = '/api/skill-api/v2/mcp'
MAX_BYTES = 32 * 1024 * 1024
PROTOCOL = '2025-03-26'


class McpFailure(Failure):
    def __init__(self, kind, message, code=None):
        super().__init__(message)
        self.kind, self.code = kind, code


def http_failure(status):
    kind = {401: 'AUTH_REQUIRED', 403: 'PERMISSION_DENIED', 402: 'PAYMENT_REQUIRED',
            429: 'RATE_LIMITED', 404: 'UNAVAILABLE'}.get(status, 'UPSTREAM_ERROR' if status >= 500 else 'HTTP_ERROR')
    return McpFailure(kind, 'MCP HTTP ' + str(status) + '; no automatic retry.', status)


class McpSession:
    def __init__(self, context):
        self.context = context
        self.session = None
        self.protocol = PROTOCOL
        self.tool_calls = 0
        self.opener = build_opener(NoRedirect())

    def __enter__(self):
        try:
            result = self.request('initialize', {'protocolVersion': PROTOCOL, 'capabilities': {},
                                  'clientInfo': {'name': 'nexscope-cli', 'version': self.version()}})
            if result.get('protocolVersion') not in ('2025-03-26', '2025-06-18', '2025-11-25'):
                raise McpFailure('PROTOCOL_ERROR', 'Unsupported MCP protocol version.')
            self.protocol = result['protocolVersion']
            self.request('notifications/initialized', {}, notification=True)
            return self
        except Exception:
            self.__exit__()
            raise

    @staticmethod
    def version():
        from .. import __version__
        return __version__

    def __exit__(self, *exc):
        if self.session:
            try:
                with self.opener.open(Request(self.context.base + ENDPOINT, method='DELETE',
                                      headers=self.headers()), timeout=10):
                    pass
            except (HTTPError, URLError, TimeoutError, OSError):
                pass

    def headers(self):
        result = {'Authorization': self.context.authorization(), 'Content-Type': 'application/json',
                  'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': self.protocol,
                  **client_headers()}
        if self.session:
            result['Mcp-Session-Id'] = self.session
        return result

    def request(self, method, params, notification=False):
        ident = str(uuid.uuid4())
        payload = {'jsonrpc': '2.0', 'method': method, 'params': params}
        if not notification:
            payload['id'] = ident
        raw = json.dumps(payload, allow_nan=False).encode('utf-8')
        if len(raw) > MAX_BYTES:
            raise McpFailure('INVALID_INPUT', 'MCP input exceeds 32 MiB.')
        request = Request(self.context.base + ENDPOINT, data=raw, headers=self.headers(), method='POST')
        if method == 'tools/call':
            self.tool_calls += 1
        try:
            with self.opener.open(request, timeout=60) as response:
                if notification:
                    if response.status not in (200, 202, 204):
                        raise http_failure(response.status)
                    return None
                session = response.headers.get('Mcp-Session-Id')
                if method == 'initialize' and session:
                    if len(session) > 1024 or any(ord(c) < 33 or ord(c) > 126 for c in session):
                        raise McpFailure('PROTOCOL_ERROR', 'Invalid MCP session header.')
                    self.session = session
                if response.headers.get_content_type() == 'text/event-stream':
                    value = self.stream_result(response, ident)
                else:
                    body = response.read(MAX_BYTES + 1)
                    if len(body) > MAX_BYTES:
                        raise McpFailure('INVALID_RESPONSE', 'MCP response exceeds 32 MiB.')
                    value = decode(body)
        except HTTPError as error:
            error.close()
            raise http_failure(error.code) from None
        except (URLError, TimeoutError, OSError):
            raise McpFailure('OUTCOME_UNKNOWN', 'Network result is uncertain; no automatic retry.') from None
        if not isinstance(value, dict) or value.get('jsonrpc') != '2.0' or value.get('id') != ident:
            raise McpFailure('INVALID_RESPONSE', 'MCP response does not match its request.')
        if 'error' in value:
            error = value['error']
            code = error.get('code') if isinstance(error, dict) else None
            raise McpFailure('RPC_ERROR', 'MCP returned a protocol error; inspect the saved request.', code)
        if not isinstance(value.get('result'), dict):
            raise McpFailure('INVALID_RESPONSE', 'MCP result must be a JSON object.')
        return value['result']

    @staticmethod
    def stream_result(response, ident):
        total, data, deadline = 0, [], time.monotonic() + 180
        while time.monotonic() < deadline:
            line = response.readline(MAX_BYTES - total + 1)
            total += len(line)
            if total > MAX_BYTES:
                raise McpFailure('INVALID_RESPONSE', 'MCP event stream exceeds 32 MiB.')
            if not line:
                break
            if line in (b'\n', b'\r\n'):
                if data:
                    value = decode(b'\n'.join(data))
                    data = []
                    if isinstance(value, dict) and value.get('id') == ident:
                        return value
                    if isinstance(value, dict) and 'id' in value and 'method' in value:
                        raise McpFailure('INTERACTION_REQUIRED', 'Server requested an unsupported interactive client action.')
            elif line.startswith(b'data:'):
                data.append(line[5:].lstrip(b' ').rstrip(b'\r\n'))
        raise McpFailure('OUTCOME_UNKNOWN', 'MCP stream ended without a result; do not repeat a possibly paid call.')

    def tools(self):
        tools, names, cursors = [], set(), set()
        params = {}
        for _ in range(128):
            page = self.request('tools/list', params)
            if not isinstance(page.get('tools'), list):
                raise McpFailure('INVALID_RESPONSE', 'MCP discovery did not return tools.')
            for tool in page['tools']:
                if not isinstance(tool, dict) or not isinstance(tool.get('name'), str) or tool['name'] in names:
                    raise McpFailure('INVALID_RESPONSE', 'MCP discovery contains invalid or duplicate tool names.')
                names.add(tool['name'])
                tools.append(tool)
                if len(tools) > 4096:
                    raise McpFailure('INVALID_RESPONSE', 'MCP discovery exceeds 4096 tools.')
            cursor = page.get('nextCursor')
            if cursor is None:
                return tools
            if not isinstance(cursor, str) or not cursor or len(cursor) > 4096 or cursor in cursors:
                raise McpFailure('INVALID_RESPONSE', 'MCP discovery cursor is invalid or repeated.')
            cursors.add(cursor)
            params = {'cursor': cursor}
        raise McpFailure('INVALID_RESPONSE', 'MCP discovery exceeds 128 pages.')

    def call(self, name, arguments):
        if self.tool_calls:
            raise McpFailure('CALL_BUDGET_EXHAUSTED', 'One tool invocation per command; no automatic replay.')
        return self.request('tools/call', {'name': name, 'arguments': arguments})
