# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Evidence-linked CSV and Markdown views of the same comparison dataset."""
from collections import defaultdict
import csv
from html import escape
import io
import json
import re
from urllib.parse import quote

from ..core.datasets import FIELDS

FORMATS = {'html': '.html', 'csv': '.csv', 'markdown': '.md'}
CONNECT = 'https://github.com/nexscope-ai/nexscope-cli#connect'


def text(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def csv_cell(value):
    value = text(value)
    if value.startswith(('\t', '\r', '\n')) or value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def md_cell(value):
    value = 'Not provided' if value is None or value == '' else text(value)
    value = escape(value, quote=True)
    value = re.sub(r'([\\`*_{}\[\]()#+.!|~-])', r'\\\1', value)
    return value.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')


def grouped(dataset):
    groups = defaultdict(list)
    for row in dataset['products']:
        groups[(row['marketplace'], row['currency'], row['rating_scale'])].append(row)
    return groups


def notice(dataset):
    if dataset['sourceType'] in ('mock', 'remote'):
        return ('MOCK / FICTIONAL DATA: no live service queried; not market research.' if dataset['sourceType'] == 'mock'
                else 'REMOTE DATA: source and retrieval times are in request evidence; missing values are not inferred.')
    return 'USER IMPORT: supplied data, not refreshed or independently verified; bundled samples are fictional.'


def render_csv(dataset, evidence_name):
    stream = io.StringIO(newline='')
    columns = ('comparison_group', *FIELDS, 'source_row', 'extra', 'source_type', 'collection_status',
               'fetched_at', 'cache_hit', 'missing_fields', 'evidence_index', 'input_sha256', 'imported_at',
               'errors', 'request_accounting', 'data_notice', 'comparison_policy', 'connect_instructions')
    writer = csv.writer(stream, quoting=csv.QUOTE_ALL, lineterminator='\r\n')
    writer.writerow(columns)
    for group_id, rows in enumerate(grouped(dataset).values(), 1):
        for row in rows:
            extra = row['extra']
            values = (group_id, *(row[field] for field in FIELDS), row['source_row'], extra,
                      dataset['sourceType'], dataset.get('collectionStatus', 'IMPORTED'),
                      extra.get('fetchedAt') if dataset['sourceType'] in ('mock', 'remote') else None,
                      extra.get('cacheHit') if dataset['sourceType'] in ('mock', 'remote') else None,
                      [field for field in FIELDS if row[field] is None],
                      quote(evidence_name, safe='') + '/dataset.json', dataset['inputSha256'], dataset['importedAt'],
                      dataset.get('errors', []), dataset.get('budget'), notice(dataset),
                      'Compare only within the same market/currency/rating-scale group; no ranking or conversion.', CONNECT)
            writer.writerow([csv_cell(value) for value in values])
    # BOM helps spreadsheet apps identify UTF-8; exact source values remain in evidence.
    return '\ufeff' + stream.getvalue()


def render_markdown(dataset, evidence_name):
    groups = grouped(dataset)
    lines = ['# Product comparison', '', '**' + notice(dataset) + '**', '',
             f"{len(dataset['products'])} products across {len(groups)} comparable groups.",
             'Compare only within the same market, currency and rating scale. No cross-group ranking or conversion.', '',
             'Collection status: ' + md_cell(dataset.get('collectionStatus', 'IMPORTED')), '',
             'Imported at: ' + md_cell(dataset['importedAt']) + ' (not the observation time).', '',
             'Input SHA-256: ' + md_cell(dataset['inputSha256']), '',
             '[Evidence dataset and exact source values](' + quote(evidence_name, safe='') + '/dataset.json)', '',
             'Failed or skipped products: ' + md_cell(dataset.get('errors', [])), '',
             'Request accounting: ' + md_cell(dataset.get('budget')), '']
    fields = (*FIELDS, 'source_row', 'extra')
    for index, ((market, currency, scale), rows) in enumerate(groups.items(), 1):
        lines += [f'## Group {index}', '',
                  'Market: ' + md_cell(market) + ' / Currency: ' + md_cell(currency) + ' / Rating scale: ' + md_cell(scale), '',
                  '| ' + ' | '.join(fields) + ' |', '| ' + ' | '.join('---' for _ in fields) + ' |']
        for row in rows:
            lines.append('| ' + ' | '.join(md_cell(row[field]) for field in fields) + ' |')
        lines.append('')
    lines += ['Keep this report with its evidence directory. Missing fields remain unknown.', '',
              '[Need updated product data? Connect Nexscope](' + CONNECT + ').',
              'Optional instructions only: this report does not upload inputs or call data services.', '']
    return '\n'.join(lines)
