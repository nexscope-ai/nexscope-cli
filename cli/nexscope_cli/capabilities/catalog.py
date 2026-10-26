# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""A1 planning subset of the pinned research routes, not a live API contract."""
from copy import deepcopy
from importlib.resources import files
import json

from ..core.errors import Failure

DOMAINS = ('amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 'amazon.it',
           'amazon.es', 'amazon.co.jp', 'amazon.ca', 'amazon.com.au', 'amazon.com.br',
           'amazon.in', 'amazon.nl', 'amazon.se', 'amazon.pl', 'amazon.sg',
           'amazon.sa', 'amazon.ae', 'amazon.com.mx', 'amazon.com.tr',
           'amazon.com.be', 'amazon.cn', 'amazon.eg')
COMMON = {
    'amazonDomain': {'type': 'string', 'enum': list(DOMAINS), 'default': 'amazon.com'},
    'language': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
    'deliveryZip': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
    'device': {'type': 'string', 'enum': ['desktop', 'mobile', 'tablet'], 'default': 'desktop'},
}
CAPABILITIES = {
    'amazon-search': {
        'endpoint': '/api/v1/tools/research/amazon/search',
        'script': 'scripts/amazon_search.py',
        'properties': {**COMMON,
                       'keyword': {'type': 'string', 'minLength': 1, 'maxLength': 1024},
                       'node': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
                       'page': {'type': 'integer', 'enum': [1], 'default': 1},
                       'sort': {'type': 'string', 'enum': ['relevanceblender', 'price-asc-rank', 'price-desc-rank', 'review-rank', 'date-desc-rank', 'exact-aware-popularity-rank']}},
        'required': [],
        'anyOf': [{'required': ['keyword']}, {'required': ['node']}],
        'limits': {'pages': 1, 'automaticPagination': False, 'requireKeywordOrNode': True},
    },
    'amazon-product-detail': {
        'endpoint': '/api/v1/tools/research/amazon/product/detail',
        'script': 'scripts/amazon_product_detail.py',
        'properties': {**COMMON,
                       'asins': {'type': 'string', 'pattern': '^[A-Z0-9]+(,[A-Z0-9]+){0,2}$', 'maxLength': 4096},
                       'returnBoughtTogether': {'type': 'boolean'},
                       'returnRelatedProducts': {'type': 'boolean'},
                       'returnAuthorsReviews': {'type': 'boolean'}},
        'required': ['asins'],
        'limits': {'maxAsins': 3, 'requestStrategy': 'one-ASIN-per-request', 'duplicateAsins': 'reject'},
    },
}


def describe(name):
    if name not in CAPABILITIES:
        raise Failure('Unknown capability; supported: amazon-search, amazon-product-detail.')
    spec = deepcopy(CAPABILITIES[name])
    bundled = json.loads(files('nexscope_cli').joinpath('catalog.json').read_text(encoding='utf-8'))
    schema = {'type': 'object', 'additionalProperties': False,
              'properties': spec['properties'], 'required': spec['required']}
    if 'anyOf' in spec:
        schema['anyOf'] = spec['anyOf']
    return {
        'schemaVersion': 'nexscope.capability.v1', 'capability': name,
        'contractVersion': 'research-data-code-759d751.v1', 'status': 'EXECUTION_GATED',
        'executionAvailable': False, 'liveExecutionAvailable': True,
        'executionRequires': ['--execute', '--allow-paid'],
        'mockExecutionAvailable': True, 'method': 'POST', 'endpoint': spec['endpoint'],
        'inputSchema': schema, 'pilotLimits': spec['limits'],
        'source': {'skill': name, 'script': spec['script'],
                   'repository': bundled['source'], 'revision': bundled['skills'][name].get('sourceRevision', bundled['revision']),
                   'snapshot': bundled['skills'][name].get('sourceSnapshot'),
                   'reference': 'references/api.md',
                   'sha256': bundled['skills'][name]['files']['references/api.md']},
        'validation': 'Pinned backend source and mock verified; live samples and billing acceptance remain pending.',
        'contract': json.loads(files('nexscope_cli').joinpath('api-contract.json').read_text(encoding='utf-8')),
        'pricing': {'status': 'UNKNOWN', 'creditsPerRequest': None,
                    'source': None, 'note': 'Response cost is elapsed time, not credits.'},
    }
