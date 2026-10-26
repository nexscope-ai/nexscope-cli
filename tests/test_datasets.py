import csv
from importlib.resources import files
import io
import json
from pathlib import Path
import tempfile
import unittest

from nexscope_cli.core.datasets import DatasetError, MAX_BYTES, read_dataset
from nexscope_cli.reports.compare import compare


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, rows, name='input.json'):
        path = self.root / name
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
        return path

    def test_import_reports_and_reexports_both_formats_without_keyring(self):
        for suffix in ['csv', 'json']:
            path = self.root / ('自有 data.' + suffix)
            path.write_bytes(files('nexscope_cli.resources').joinpath('products-sample.' + suffix).read_bytes())
            for format, extension in [('html', '.html'), ('csv', '.csv'), ('markdown', '.md')]:
                output = self.root / (suffix + format + extension)
                result = compare(path, output, format=format)
                index = Path(result['evidence']) / 'dataset.json'
                first = json.loads(index.read_text(encoding='utf-8'))
                second = compare(index, self.root / ('再导出 ' + suffix + format + extension), format=format)
                self.assertEqual(second['sourceType'], 'user_import')
                self.assertEqual(json.loads((Path(second['evidence']) / 'dataset.json').read_text(encoding='utf-8')), first)

    def test_invalid_rows_are_reported_without_silent_loss(self):
        path = self.write([{'product_id': 'A', 'title': 'A', 'price': 'NaN'},
                           {'product_id': 'A', 'title': '', 'rating': 7, 'rating_scale': 5},
                           {'product_id': 1, 'title': 'B', 'price': 0},
                           {'product_id': 'C', 'title': 'C', 'rating_scale': '1e9999999'}])
        with self.assertRaises(DatasetError) as failure:
            read_dataset(path)
        issues = failure.exception.issues
        self.assertEqual({item['row'] for item in issues}, {1, 2, 3, 4})
        self.assertTrue(any(item['field'] == 'currency' for item in issues))
        self.assertTrue(any('Duplicate' in item['message'] for item in issues))

    def test_encoding_duplicate_headers_keys_and_extra_csv_columns(self):
        invalid = [('bad.json', b'\xff'), ('keys.json', b'[{"product_id":"A","product_id":"B","title":"T"}]'),
                   ('overflow.json', b'[{"product_id":"A","title":"T","extra_number":1e9999}]'),
                   ('headers.csv', b'product_id,title,title\nA,B,C'),
                   ('columns.csv', b'product_id,title\nA,B,C'),
                   ('boolean.json', b'[{"product_id":"A","title":"T","price":true,"currency":"USD"}]')]
        for name, raw in invalid:
            file = self.root / name
            file.write_bytes(raw)
            with self.subTest(name=name), self.assertRaises(DatasetError):
                read_dataset(file)

    def test_html_markdown_and_csv_escape_user_values(self):
        path = self.write([{'product_id': '=SUM(1,1)', 'title': '<script>alert(1)</script> [click](javascript:x)',
                            'marketplace': 'M', 'price': 0, 'currency': 'USD', 'source_url': 'https://example.invalid/?a=1&b=2'},
                           {'product_id': '@formula', 'title': '\t=1+1', 'marketplace': 'N'}])
        for format, suffix in [('html', '.html'), ('csv', '.csv'), ('markdown', '.md')]:
            output = self.root / ('safe' + suffix)
            compare(path, output, format=format)
            content = output.read_text(encoding='utf-8-sig')
            if format == 'csv':
                rows = list(csv.DictReader(io.StringIO(content)))
                self.assertTrue(rows[0]['product_id'].startswith("'="))
                self.assertTrue(rows[1]['product_id'].startswith("'@"))
            else:
                self.assertNotIn('<script>', content)
                self.assertIn('&lt;script&gt;', content)
        bad = self.write([{'product_id': 'A', 'title': 'A', 'source_url': 'javascript:alert(1)'}])
        with self.assertRaises(DatasetError):
            read_dataset(bad)

    def test_capacity_10000_rows_and_size_limit(self):
        rows = [{'product_id': str(i), 'title': 'Product ' + str(i)} for i in range(10000)]
        path = self.write(rows)
        result = compare(path, self.root / 'capacity.csv', format='csv')
        self.assertEqual(result['rows'], 10000)
        self.assertEqual(len(read_dataset(Path(result['evidence']) / 'dataset.json')[0]['products']), 10000)
        rows.append({'product_id': 'overflow', 'title': 'Overflow'})
        with self.assertRaises(DatasetError):
            read_dataset(self.write(rows))
        huge = self.root / 'huge.csv'
        huge.write_bytes(b'product_id,title\nA,' + b'x' * MAX_BYTES)
        with self.assertRaises(DatasetError):
            read_dataset(huge)

    def test_csv_field_can_exceed_the_stdlib_default_within_file_limit(self):
        path = self.root / 'large-field.csv'
        path.write_text('product_id,title\nA,' + 'x' * 200000, encoding='utf-8')
        previous_limit = csv.field_size_limit()
        dataset, _ = read_dataset(path)
        self.assertEqual(len(dataset['products'][0]['title']), 200000)
        self.assertEqual(csv.field_size_limit(), previous_limit)

    def test_near_limit_input_can_reimport_its_larger_normalized_dataset(self):
        rows = [{'product_id': str(i), 'title': 'x' * 980} for i in range(10000)]
        path = self.write(rows)
        self.assertLess(path.stat().st_size, MAX_BYTES)
        result = compare(path, self.root / 'large.csv', format='csv')
        dataset = Path(result['evidence']) / 'dataset.json'
        self.assertGreater(dataset.stat().st_size, MAX_BYTES)
        self.assertEqual(len(read_dataset(dataset)[0]['products']), 10000)

    def test_dry_run_and_existing_outputs_do_not_write(self):
        path = self.write([{'product_id': 'A', 'title': 'A'}])
        output = self.root / 'report.html'
        result = compare(path, output, dry_run=True)
        self.assertEqual(result['networkCalls'], 0)
        self.assertFalse(output.exists())
        with self.assertRaises(NotADirectoryError):
            compare(path, self.root / 'missing' / 'report.html', dry_run=True)
        self.assertFalse((self.root / 'missing').exists())
        output.write_text('keep')
        with self.assertRaises(FileExistsError):
            compare(path, output, dry_run=True)
        with self.assertRaises(FileExistsError):
            compare(path, output)
        self.assertEqual(output.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
