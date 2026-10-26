# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Resolve a selected authentication context only after an explicit execution decision."""
from .auth import DEFAULT_ORIGIN, resolve_auth
from .errors import Failure
from .execution import Executor
from .transport import HttpTransport


def engine_for(args):
    if args.mock:
        from ..capabilities.mock import executor
        return executor(args.auth_mode, args.mock, args.max_calls)
    if not args.allow_paid:
        raise Failure('Remote execution requires --allow-paid.')
    loader = None
    if args.auth_mode == 'browser-account':
        from ..main import Client
        client = Client(args.api_base or DEFAULT_ORIGIN)
        loader = lambda: client.load('credential')
    context = resolve_auth(args.auth_mode, base=args.api_base, credential_loader=loader)
    return Executor(context, HttpTransport(), max_calls=args.max_calls)
