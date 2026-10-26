"""Generate public fictional examples from the same packaged resources as the CLI."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cli'))
from nexscope_cli.core.datasets import DatasetError
from nexscope_cli.reports.compare import compare, resource


def main():
    target = ROOT / 'examples'
    target.mkdir(exist_ok=True)
    for name in ('fields.json', 'products.schema.json', 'products-template.csv', 'products-sample.csv', 'products-sample.json'):
        (target / name).write_bytes(resource(name).read_bytes())
    for format, suffix in [('html', 'html'), ('csv', 'csv'), ('markdown', 'md')]:
        output = target / ('comparison.' + suffix)
        if output.exists() or output.with_name(output.name + '.evidence').exists():
            raise SystemExit('Examples already exist; review changes and regenerate in an empty staging checkout.')
        compare(target / 'products-sample.json', output, format=format)
    invalid = target / 'invalid-products.csv'
    invalid.write_text('product_id,title,price,currency\nexample-1,Fictional product,12.50,\n', encoding='utf-8', newline='\n')
    try:
        compare(invalid, target / 'must-not-exist.html')
    except DatasetError as error:
        (target / 'invalid-products-error.json').write_text(json.dumps({'status': 'INVALID_INPUT',
             'message': str(error), 'issues': error.issues}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    else:
        raise AssertionError('The invalid example unexpectedly passed')
    assert not (target / 'must-not-exist.html').exists()
    print('Generated public inputs, field/schema resources, three reports, evidence and a reproducible error example.')


if __name__ == '__main__':
    main()
