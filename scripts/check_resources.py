"""Verify current bundled hashes; --update records intentional adapter changes."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import tomllib
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    package = root / 'cli' / 'nexscope_cli'
    version = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    catalog = json.loads((package / 'catalog.json').read_text())
    lock = tomllib.loads((root / 'uv.lock').read_text())
    locked_version = next(item['version'] for item in lock['package'] if item['name'] == 'nexscope-cli')
    dependency_version = json.loads((package / 'dependency-lock.json').read_text())['version']
    module = ast.parse((package / '__init__.py').read_text())
    code_version = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == '__version__' for target in node.targets))
    if not (locked_version == dependency_version == code_version == version):
        raise SystemExit('Package version files disagree.')
    dependency = json.loads((package / 'dependency-lock.json').read_text(encoding='utf-8'))
    for source, key in [(root / 'uv.lock', 'lockSha256'), (package / 'dependencies.lock', 'requirementsSha256')]:
        if hashlib.sha256(source.read_bytes()).hexdigest() != dependency[key]:
            raise SystemExit('Dependency lock digest mismatch: ' + source.name)
    sys.path.insert(0, str(root / 'cli'))
    from nexscope_cli.tools import catalog as tool_catalog, digest
    tools = tool_catalog()
    contract = json.loads((package / 'api-contract.json').read_text(encoding='utf-8'))
    if contract['toolCatalog']['sha256'] != tools['sha256'] or contract['toolCatalog']['count'] != len(tools['tools']):
        raise SystemExit('API contract and tool catalog disagree.')
    if set(contract['toolBindings']) != {t['name'] for t in tools['tools']}:
        raise SystemExit('API contract does not cover the full tool catalog.')
    for tool in tools['tools']:
        if contract['toolBindings'][tool['name']]['inputSchemaSha256'] != digest(tool['inputSchema']):
            raise SystemExit('Tool binding schema digest mismatch: ' + tool['name'])
    for name, entry in catalog['skills'].items():
        for relative, expected in entry['files'].items():
            file = package / 'skills' / name / relative
            actual = hashlib.sha256(file.read_bytes()).hexdigest()
            if args.update:
                entry['files'][relative] = actual
            elif actual != expected:
                raise SystemExit('Bundled resource hash mismatch: ' + name + '/' + relative)
        requirement = (package / 'skills' / name / 'requirements.txt').read_text().strip()
        if requirement != 'nexscope-cli==' + version:
            raise SystemExit('Adapter requires the wrong CLI version: ' + name)
        for script in entry['scripts']:
            module = ast.parse((package / 'skills' / name / script).read_text())
            required = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
                            and any(isinstance(target, ast.Name) and target.id == 'REQUIRED_VERSION' for target in node.targets))
            if required != version:
                raise SystemExit('Adapter script requires the wrong CLI version: ' + name)
    if args.update:
        (package / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Current resource hashes and adapter requirements verified: ' + version)


if __name__ == '__main__':
    main()
