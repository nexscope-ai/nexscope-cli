# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Shared CLI errors with credential-free messages."""


class Failure(Exception):
    pass


class AuthRequired(Failure):
    pass
