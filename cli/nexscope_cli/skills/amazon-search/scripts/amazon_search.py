#!/usr/bin/env python3
# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Independent Skill compatibility entrypoint; install the paired local wheel."""
import sys

INDEPENDENT_COMPAT_API = 1
REQUIRED_VERSION = '0.1.5'


def main():
    try:
        from nexscope_cli import __version__
        from nexscope_cli.compat import COMPAT_API_VERSION
        from nexscope_cli.compat.legacy import main as run
    except ImportError:
        print('Dependency missing: install nexscope-cli==0.1.5 from the paired local wheel using this Python interpreter. No request was sent.', file=sys.stderr)
        return 1
    if __version__ != REQUIRED_VERSION or COMPAT_API_VERSION != INDEPENDENT_COMPAT_API:
        print('Dependency mismatch: this adapter requires nexscope-cli==0.1.5 and compatibility API 1. Install the paired wheel or restore the previous Skill directory. No request was sent.', file=sys.stderr)
        return 1
    return run('amazon-search')


if __name__ == '__main__':
    sys.exit(main())
