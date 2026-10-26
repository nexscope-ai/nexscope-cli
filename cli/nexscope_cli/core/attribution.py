# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Allowlisted client provenance; never contains credentials or user input."""
from .. import __version__

CLIENTS = ('python-cli', 'codex-plugin', 'claude-code')
CHANNELS = ('github', 'marketplace', 'local', 'unknown')
ENTRYPOINTS = ('cli', 'plugin', 'report')
CAMPAIGN = 'cli-data-release'


def source(client='python-cli', channel='unknown', entrypoint='cli'):
    if client not in CLIENTS or channel not in CHANNELS or entrypoint not in ENTRYPOINTS:
        raise ValueError('Unsupported attribution value.')
    return {'version': 1, 'client': client, 'clientVersion': __version__,
            'channel': channel, 'campaign': CAMPAIGN, 'entrypoint': entrypoint}


def headers():
    return {'X-Nexscope-Client': 'python-cli', 'X-Nexscope-Client-Version': __version__}
