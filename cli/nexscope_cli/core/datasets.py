# Copyright 2026 Nexscope
# SPDX-License-Identifier: Apache-2.0
"""Validate user-owned UTF-8 data without accessing credentials or the network."""
import csv
from datetime import datetime, timezone
from decimal import Decimal, DecimalException, InvalidOperation
import hashlib
import io
from pathlib import Path
import re
from urllib.parse import urlsplit

from .errors import Failure
from .evidence import MAX_FILE_BYTES, decode, read_bundle, timestamp, validate_request

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 10000
FIELDS = (
    'product_id', 'title', 'marketplace', 'price', 'currency', 'rating',
    'rating_scale', 'review_count', 'source_url', 'observed_at',
)


class DatasetError(ValueError):
    def __init__(self, issues):
        super().__init__('Input validation failed; no rows were silently discarded.')
        self.issues = issues


def safe_url(value):
    try:
        url = urlsplit(value)
        return (url.scheme in ('https', 'http') and bool(url.hostname)
                and not url.username and not url.password
                and not any(c.isspace() or ord(c) < 32 for c in value))
    except ValueError:
        return False


def product(result, market):
    """Map documented remote fields once, preserving explicit zero values."""
    raw = result['response']['data']['products'][0]
    price = raw['extractedPrice'] if raw.get('extractedPrice') is not None else raw.get('price')
    raw_currency = raw.get('currency')
    currency = raw_currency if isinstance(raw_currency, str) and re.fullmatch(r'[A-Z]{3}', raw_currency) else None
    row = dict.fromkeys(FIELDS)
    row.update(product_id=raw['asin'], title=raw['title'], marketplace=market,
               price=price if currency else None,
               currency=currency, rating=raw.get('rating') if raw.get('ratingScale') else None,
               rating_scale=raw.get('ratingScale'), review_count=raw.get('ratings', raw.get('reviews')))
    link = raw.get('asinUrl') or raw.get('linkClean') or raw.get('link')
    row['source_url'] = link if isinstance(link, str) and safe_url(link) else None
    row['source_row'] = 1
    row['extra'] = {'evidenceFile': 'request-' + str(result['sequence']) + '.json',
                    'sourcePointer': '/response/data/products/0', 'fetchedAt': result['fetchedAt'],
                    'cacheHit': result['cacheHit'], 'contractVersion': result['contractVersion'],
                    'missingFields': [field for field in FIELDS if row[field] is None]}
    if raw_currency is not None and currency is None:
        row['extra'].update(unresolvedCurrency=raw_currency, unresolvedPrice=price)
    return row


def read_dataset(filename):
    path = Path(filename)
    limit = MAX_BYTES if path.suffix.lower() == '.csv' else MAX_FILE_BYTES
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise DatasetError([{'row': 0, 'field': 'file', 'message': 'Input exceeds its size limit (10 MiB user input, 32 MiB versioned dataset).'}])
    envelope = None
    try:
        text = raw.decode('utf-8-sig')
        if path.suffix.lower() == '.csv':
            previous_limit = csv.field_size_limit(MAX_BYTES)
            try:
                reader = csv.DictReader(io.StringIO(text, newline=''), strict=True)
                headers = reader.fieldnames or []
                if len(headers) != len(set(headers)) or not {'product_id', 'title'} <= set(headers):
                    raise ValueError('CSV needs unique headers including product_id and title.')
                rows = []
                for row in reader:
                    if len(rows) >= MAX_ROWS:
                        raise ValueError('Maximum input is 10000 products; split the file.')
                    rows.append(row)
            finally:
                csv.field_size_limit(previous_limit)
        elif path.suffix.lower() == '.json':
            rows = decode(raw)
            if isinstance(rows, dict):
                envelope, rows = rows, rows.get('products')
            if not isinstance(rows, list):
                raise ValueError('JSON must be an array of products or a versioned dataset with products.')
        else:
            raise ValueError('Use a .csv or .json file.')
    except (UnicodeError, ValueError, csv.Error, RecursionError, Failure) as error:
        raise DatasetError([{'row': 0, 'field': 'file', 'message': str(error)}]) from None
    if envelope is None and len(raw) > MAX_BYTES:
        raise DatasetError([{'row': 0, 'field': 'file', 'message': 'Maximum input size is 10 MiB; split the file.'}])
    products = validate_rows(rows, csv_input=path.suffix.lower() == '.csv', versioned=envelope is not None)
    if envelope is not None:
        try:
            validate_dataset(envelope, path, raw)
        except (Failure, OSError, KeyError, TypeError, ValueError):
            raise DatasetError([{'row': 0, 'field': 'evidence', 'message': 'Invalid or incomplete versioned dataset evidence; keep the complete original output directory.'}]) from None
        return envelope, raw
    return {
        'schemaVersion': 1, 'sourceType': 'user_import',
        'inputName': 'input' + path.suffix.lower(), 'originalInputName': path.name, 'inputSha256': hashlib.sha256(raw).hexdigest(),
        'importedAt': datetime.now(timezone.utc).isoformat(), 'products': products,
    }, raw


def validate_rows(rows, *, csv_input=False, versioned=False):
    if not isinstance(rows, list) or (not rows and not versioned) or len(rows) > MAX_ROWS:
        raise DatasetError([{'row': 0, 'field': 'file', 'message': 'Provide 1 to 10000 products; no account is required.'}])
    issues, products, seen = [], [], set()
    for index, row in enumerate(rows, 1):
        # CSV row is a logical record number, with its header counted as row 1.
        row_number = index + csv_input
        def issue(field, message):
            issues.append({'row': row_number, 'field': field, 'message': message})
        if not isinstance(row, dict):
            issue('record', 'Expected a product object.')
            continue
        if None in row:
            issue('record', 'CSV record has more values than headers.')
        product = {}
        for field in FIELDS:
            value = row.get(field)
            if value is None or value == '':
                product[field] = None
            elif field in ('price', 'rating', 'rating_scale', 'review_count'):
                try:
                    if isinstance(value, bool):
                        raise InvalidOperation
                    number = Decimal(str(value).strip())
                    if not number.is_finite() or number < 0:
                        raise InvalidOperation
                    if field == 'rating_scale' and number == 0:
                        raise InvalidOperation
                    if field == 'review_count' and number != number.to_integral_value():
                        raise InvalidOperation
                    product[field] = str(number.normalize()) if field == 'rating_scale' else str(number)
                except (DecimalException, ValueError):
                    product[field] = None
                    issue(field, 'Expected a finite non-negative number, positive scale, or integer count as applicable.')
            elif not isinstance(value, str):
                product[field] = None
                issue(field, 'Expected a string; identifiers must remain strings.')
            else:
                product[field] = value.strip() or None
        for field in ('product_id', 'title'):
            if not product[field]:
                issue(field, 'Required non-empty string.')
        identity = (product['marketplace'], product['product_id'])
        if product['product_id'] and identity in seen:
            issue('product_id', 'Duplicate identifier within this marketplace.')
        seen.add(identity)
        if product['price'] is not None and not product['currency']:
            issue('currency', 'Required when price is supplied.')
        if product['currency'] and not re.fullmatch(r'[A-Z]{3}', product['currency']):
            issue('currency', 'Use a three-letter uppercase currency code.')
        if product['rating'] is not None:
            if product['rating_scale'] is None:
                issue('rating_scale', 'Required when rating is supplied.')
            elif Decimal(product['rating']) > Decimal(product['rating_scale']):
                issue('rating', 'Rating exceeds its scale.')
        if product['source_url'] and not safe_url(product['source_url']):
            issue('source_url', 'Use an HTTP(S) URL without credentials or whitespace.')
        if product['observed_at']:
            try:
                moment = datetime.fromisoformat(product['observed_at'].replace('Z', '+00:00'))
                if moment.tzinfo is None:
                    raise ValueError
            except ValueError:
                issue('observed_at', 'Use an ISO 8601 timestamp with a timezone.')
        if versioned:
            if (not set(FIELDS) <= set(row) or type(row.get('source_row')) is not int or row['source_row'] < 1
                    or not isinstance(row.get('extra'), dict)):
                issue('record', 'Versioned products require all fields, a positive source_row and an extra object.')
            product['source_row'] = row.get('source_row')
            product['extra'] = row.get('extra')
        else:
            product['source_row'] = row_number
            product['extra'] = {k: v for k, v in row.items() if k is not None and k not in FIELDS}
        products.append(product)
    if issues:
        raise DatasetError(issues)
    return products


def validate_dataset(dataset, path, raw):
    if (type(dataset.get('schemaVersion')) is not int or dataset['schemaVersion'] != 1
            or dataset.get('sourceType') not in ('user_import', 'mock', 'remote')
            or not timestamp(dataset.get('importedAt'))
            or dataset.get('inputName') not in ('plan.json', 'input.csv', 'input.json')
            or not isinstance(dataset.get('inputSha256'), str)
            or not re.fullmatch('[0-9a-f]{64}', dataset['inputSha256'])):
        raise Failure('Invalid dataset metadata.')
    bundle = read_bundle(path.parent)
    if (bundle.get('dataset.json') != raw or dataset['inputName'] not in bundle
            or hashlib.sha256(bundle[dataset['inputName']]).hexdigest() != dataset['inputSha256']):
        raise Failure('Dataset input hash mismatch.')
    if dataset['sourceType'] == 'user_import':
        if dataset['inputName'] not in ('input.csv', 'input.json'):
            raise Failure('Invalid user-import evidence.')
        if dataset['inputName'] == 'input.json' and not isinstance(decode(bundle['input.json']), list):
            raise Failure('Original imported JSON must be a product array.')
        original, _ = read_dataset(path.parent / dataset['inputName'])
        if original['products'] != validate_rows(dataset['products'], versioned=True):
            raise Failure('Imported products disagree with original input.')
        return bundle
    if dataset['inputName'] != 'plan.json':
        raise Failure('Remote or mock datasets require their comparison plan.')
    from ..capabilities.plan import plan

    saved_plan = decode(bundle['plan.json'])
    if (not isinstance(saved_plan, dict) or saved_plan.get('schemaVersion') != 'nexscope.comparison-plan.v1'
            or not isinstance(saved_plan.get('execution'), dict)
            or saved_plan['execution'].get('sourceType') != dataset['sourceType']):
        raise Failure('Invalid dataset plan.')
    requests = [validate_request(decode(bundle[name])) for name in sorted(bundle) if re.fullmatch(r'request-[1-4]\.json', name)]
    if not requests or [item['sequence'] for item in requests] != list(range(1, len(requests) + 1)):
        raise Failure('Incomplete request evidence.')
    mode, base, market = saved_plan.get('authMode'), saved_plan['execution'].get('origin'), saved_plan.get('marketplace')
    chosen = saved_plan.get('asins') or saved_plan.get('selectedAsins')
    rebuilt = plan('amazon-product-detail', {'asins': chosen, 'amazonDomain': market},
                   max_calls=saved_plan.get('maxCalls'), auth_mode=mode)
    if (len(rebuilt['requests']) < 2
            or sum(bool(saved_plan.get(key)) for key in ('asins', 'keyword', 'importedSearch')) != 1
            or (saved_plan.get('asins') and saved_plan.get('selectedAsins') is not None)):
        raise Failure('Invalid comparison input scope.')
    details = [item for item in requests if item['capability'] == 'amazon-product-detail']
    if ([item['params'] for item in details] != [item['body'] for item in rebuilt['requests']]
            or any(item['authMode'] != mode or item['origin'] != base for item in requests)
            or any(item['params'].get('amazonDomain') != market for item in requests)
            or (dataset['sourceType'] == 'mock' and base != 'https://mock.invalid')):
        raise Failure('Dataset request scope mismatch.')
    searches = [item for item in requests if item['capability'] == 'amazon-search']
    planned_steps = [rebuilt]
    if searches:
        search = searches[0]
        search_plan = decode(bundle['search-plan.json']) if saved_plan.get('importedSearch') else saved_plan
        planned = plan('amazon-search', {'keyword': search_plan.get('keyword'), 'amazonDomain': market},
                       auth_mode=mode, max_calls=saved_plan['maxCalls'])
        if not saved_plan.get('importedSearch'):
            planned_steps.insert(0, planned)
        if (len(searches) != 1 or search['sequence'] != 1 or search['status'] != 'SUCCESS'
                or search['params'] != planned['requests'][0]['body']
                or not set(chosen.split(',')) <= {row['asin'] for row in search['response']['data']['products']}
                or decode(bundle['candidates.json']) != search['response']['data']['products']):
            raise Failure('Invalid search selection evidence.')
        imported = saved_plan.get('importedSearch')
        if imported:
            original_result = decode(bundle['search-result.json'])
            if (not isinstance(imported, dict) or imported.get('historical') is not True
                    or imported.get('sourceType') != dataset['sourceType'] or imported.get('authMode') != mode
                    or imported.get('origin') != base or imported.get('fetchedAt') != search['fetchedAt']
                    or imported.get('cacheHit') is not False or imported.get('requestsSent') != 1
                    or imported.get('evidenceFile') != 'request-1.json' or imported.get('planFile') != 'search-plan.json'
                    or imported.get('planSha256') != hashlib.sha256(bundle['search-plan.json']).hexdigest()
                    or not isinstance(original_result, dict) or original_result.get('status') != 'CANDIDATES_READY'
                    or original_result.get('sourceType') != dataset['sourceType']
                    or original_result.get('candidates') != search['response']['data']['products']):
                raise Failure('Invalid imported search provenance.')
    elif saved_plan.get('keyword') or saved_plan.get('importedSearch'):
        raise Failure('Search evidence is missing.')
    steps = saved_plan.get('steps')
    if (not isinstance(steps, list) or len(steps) != len(planned_steps)
            or saved_plan.get('maximumRequests') != len(requests)):
        raise Failure('Invalid dataset request plan.')
    for step, expected_step in zip(steps, planned_steps):
        if (not isinstance(step, dict)
                or any(step.get(key) != expected_step[key] for key in ('capability', 'contractVersion', 'source', 'requests'))
                or not isinstance(step.get('auth'), dict) or step['auth'].get('mode') != mode
                or step['auth'].get('origin') != base):
            raise Failure('Dataset plan disagrees with registered request contracts.')
    successful = [item for item in details if item['status'] == 'SUCCESS']
    expected = [product(item, market) for item in successful]
    for row, item in zip(expected, successful):
        row['extra']['evidenceSha256'] = hashlib.sha256(bundle['request-' + str(item['sequence']) + '.json']).hexdigest()
    if validate_rows(dataset['products'], versioned=True) != validate_rows(expected, versioned=True):
        raise Failure('Dataset products disagree with their request evidence.')
    errors = [{'asin': item['params']['asins'], 'status': item['status'], 'error': item['error']}
              for item in details if item['status'] != 'SUCCESS']
    status = ('COMPLETE' if not errors else 'PARTIAL') if len(successful) >= 2 else 'INSUFFICIENT_DATA'
    budget = dataset.get('budget')
    sent = sum(item['status'] != 'SKIPPED' and not item['cacheHit'] for item in requests)
    if (dataset.get('errors') != errors or dataset.get('collectionStatus') != status
            or not isinstance(budget, dict) or type(budget.get('requestsSent')) is not int
            or budget['requestsSent'] != sent or budget.get('maxCalls') != saved_plan['maxCalls']
            or budget.get('cacheHits') != sum(item['cacheHit'] for item in requests)
            or budget.get('importedRequests') != (1 if saved_plan.get('importedSearch') else 0)
            or budget.get('requestsSentThisRun') != sent - budget.get('importedRequests', 0)
            or budget.get('automaticRetries') != 0 or budget.get('estimatedCredits') is not None
            or budget.get('billingCap') is not None or budget.get('pricingStatus') != 'UNKNOWN'
            or sent > saved_plan['maxCalls']):
        raise Failure('Dataset collection status or accounting mismatch.')
    result = decode(bundle['result.json'])
    if (not isinstance(result, dict) or result.get('schemaVersion') != 'nexscope.comparison-result.v1'
            or result.get('status') != status or result.get('sourceType') != dataset['sourceType']
            or result.get('budget') != budget or result.get('errors') != errors
            or result.get('succeeded') != len(successful) or result.get('requested') != len(details)):
        raise Failure('Dataset disagrees with its collection result.')
    return bundle
