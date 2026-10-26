import json
from pathlib import Path
import tempfile
import unittest

from nexscope_cli.capabilities.mock import executor
from nexscope_cli.core.execution import validate_response
from nexscope_cli.reports.compare import compare as report
from nexscope_cli.workflows.compare import compare


ASINS = 'B000000001,B000000002'


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_price_contract_fields_and_invalid_numbers(self):
        for values, expected in [({'price': 19.99}, 19.99),
                                 ({'price': 10, 'extractedPrice': 0}, 0),
                                 ({'extractedPrice': 12.5}, 12.5),
                                 ({'extractedPrice': None, 'price': 0}, 0)]:
            with self.subTest(values=values):
                engine = executor('browser-account', 'complete', 3)
                for row in engine.transport.fixture['products']:
                    row.pop('extractedPrice', None)
                    row.update(values, currency='USD')
                folder = self.root / str(len(list(self.root.iterdir())))
                compare(engine, folder, asins=ASINS, mock=True)
                dataset = json.loads((folder / 'dataset.json').read_text())
                self.assertEqual(dataset['products'][0]['price'], expected)
        for value in [True, -1, '19.99', float('nan'), float('inf')]:
            payload = {'code': 0, 'data': {'products': [{'asin': 'A', 'title': 'A', 'price': value}]}}
            self.assertEqual(validate_response(200, payload, 'amazon-search', {})[0], 'INVALID_PRODUCT')

    def test_resume_does_not_search_again_and_counts_history(self):
        first = self.root / 'candidates'
        compare(executor('browser-account', 'complete', 3), first, keyword='lamp', mock=True)
        engine = executor('browser-account', 'complete', 3)
        result = compare(engine, self.root / 'finished', resume=first, selected=ASINS, mock=True)
        self.assertEqual(result['status'], 'COMPLETE')
        self.assertEqual(result['budget']['requestsSent'], 3)
        self.assertEqual(result['budget']['importedRequests'], 1)
        self.assertEqual(result['budget']['cacheHits'], 0)
        self.assertEqual(len(engine.transport.calls), 2)
        self.assertTrue(all(call[0].endswith('/product/detail') for call in engine.transport.calls))
        self.assertTrue((self.root / 'finished' / 'request-1.json').exists())

    def test_symbol_currency_keeps_product_and_unresolved_price_without_guessing(self):
        engine = executor('browser-account', 'complete', 3)
        for row in engine.transport.fixture['products']:
            row.update(currency='$', price=15.27, extractedPrice=15.27)
        folder = self.root / 'symbol'
        result = compare(engine, folder, asins=ASINS, mock=True)
        self.assertEqual(result['status'], 'COMPLETE')
        dataset = json.loads((folder / 'dataset.json').read_text(encoding='utf-8'))
        for row in dataset['products']:
            self.assertIsNone(row['currency'])
            self.assertIsNone(row['price'])
            self.assertEqual(row['extra']['unresolvedCurrency'], '$')
            self.assertEqual(row['extra']['unresolvedPrice'], 15.27)
        exported = report(folder / 'dataset.json', self.root / 'symbol.html')
        self.assertEqual(exported['rows'], 2)

    def test_remote_currency_metadata_requires_a_string(self):
        for value in [42, True, {}, []]:
            payload = {'code': 0, 'data': {'products': [{'asin': 'A', 'title': 'A', 'currency': value}]}}
            with self.subTest(value=value):
                self.assertEqual(validate_response(200, payload, 'amazon-search', {})[0], 'INVALID_PRODUCT')

    def test_workflow_dataset_can_be_reported_offline_with_evidence(self):
        folder = self.root / 'workflow'
        compare(executor('browser-account', 'partial', 3), folder,
                asins=ASINS + ',B000000003', mock=True)
        original = json.loads((folder / 'dataset.json').read_text())
        for format, suffix in [('html', '.html'), ('csv', '.csv'), ('markdown', '.md')]:
            with self.subTest(format=format):
                output = self.root / ('offline' + suffix)
                result = report(folder / 'dataset.json', output, format=format)
                self.assertEqual(result['sourceType'], 'mock')
                copied = json.loads((Path(result['evidence']) / 'dataset.json').read_text())
                self.assertEqual(copied, original)
                for row in copied['products']:
                    self.assertTrue((Path(result['evidence']) / row['extra']['evidenceFile']).is_file())
                self.assertEqual(copied['collectionStatus'], 'PARTIAL')
                self.assertTrue(copied['errors'])


if __name__ == '__main__':
    unittest.main()
