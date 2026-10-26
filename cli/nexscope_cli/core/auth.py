# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Explicit, immutable authentication snapshots; never discover a fallback."""
from dataclasses import dataclass, field
import os
from urllib.parse import urlsplit
import uuid

from .errors import AuthRequired, Failure

MODES = ('browser-account', 'env-api-key')
DEFAULT_ORIGIN = 'https://api.nexscope.ai'


def origin(value):
    try:
        if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError
        p = urlsplit(value)
        if (p.scheme != 'https' and not (p.scheme == 'http' and p.hostname in ('localhost', '127.0.0.1'))) or not p.hostname or p.username or p.password or p.query or p.fragment or p.path not in ('', '/'):
            raise ValueError
        # Validate malformed ports before a request can contain a credential.
        p.port
    except ValueError:
        raise Failure('Use an HTTPS API origin (HTTP is allowed only on loopback).') from None
    return value.rstrip('/')


@dataclass(frozen=True)
class AuthContext:
    mode: str
    base: str
    _key: str = field(repr=False)
    _session: str = field(default_factory=lambda: uuid.uuid4().hex, repr=False)

    def __post_init__(self):
        if self.mode not in MODES:
            raise Failure('Choose an explicit supported authentication mode.')
        object.__setattr__(self, 'base', origin(self.base))
        if not isinstance(self._key, str) or not self._key or any(c.isspace() or ord(c) < 32 for c in self._key):
            raise AuthRequired('AUTH_REQUIRED: the selected context has no valid API key.')

    def authorization(self):
        """Secret-bearing value: only pass to the selected origin's transport."""
        return 'Bearer ' + self._key

    def script_environment(self, inherited=None):
        """Pass credentials only to a child process, never persist this mapping."""
        env = dict(os.environ if inherited is None else inherited)
        env.update(NEXSCOPE_API_KEY=self._key, NEXSCOPE_PROXY_BASE=self.base)
        env.pop('PYTHONPATH', None)
        return env

    def redact(self, text):
        return text.replace(self._key, '[REDACTED]')

    @property
    def cache_partition(self):
        # A1 has no shared persistent cache. New snapshots never share a session,
        # even when keys rotate or two accounts use the same origin/profile.
        return self.mode, self.base, self._session


def resolve_auth(mode, *, base=None, credential_loader=None, environment=None):
    """Resolve just the selected source. Offline planning must not call this."""
    if mode == 'browser-account':
        selected_base = origin(base if base is not None else DEFAULT_ORIGIN)
        credential = credential_loader() if credential_loader is not None else None
        if not isinstance(credential, dict) or not credential.get('apiKey'):
            raise AuthRequired('AUTH_REQUIRED: run nexscope auth login.')
        return AuthContext(mode, selected_base, credential['apiKey'])
    if mode == 'env-api-key':
        if base is not None:
            raise Failure('env-api-key uses NEXSCOPE_PROXY_BASE; do not supply a browser API origin.')
        env = os.environ if environment is None else environment
        key = env.get('NEXSCOPE_API_KEY', '').strip()
        selected_base = env.get('NEXSCOPE_PROXY_BASE', '').strip()
        if not key or not selected_base:
            raise AuthRequired('AUTH_REQUIRED: configure NEXSCOPE_API_KEY and NEXSCOPE_PROXY_BASE.')
        return AuthContext(mode, selected_base, key)
    raise Failure('Choose an explicit supported authentication mode.')
