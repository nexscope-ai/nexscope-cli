from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from nexscope_cli.capabilities.mock import executor
from nexscope_cli.core.auth import AuthContext
from nexscope_cli.core.datasets import DatasetError, read_dataset
from nexscope_cli.core.errors import Failure
from nexscope_cli.core.evidence import read_bundle
from nexscope_cli.main import main
from nexscope_cli.reports.compare import compare as report
from nexscope_cli.workflows.compare import compare, workflow_plan

ASINS = 'B000000001,B000000002'


def rewrite(folder, name, mutate):
    file = folder / name
    value = json.loads(file.read_text(encoding='utf-8'))
    mutate(value)
    file.write_text(json.dumps(value), encoding='utf-8')
    manifest = folder / 'manifest.json'
    index = json.loads(manifest.read_text())
    index['files'][name] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(index), encoding='utf-8')


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.first = self.root / 'first'
        compare(executor('browser-account', 'complete', 4), self.first, keyword='lamp', mock=True)

    def test_resume_validates_selection_budget_source_market_and_mode_before_transport(self):
        invalid = [dict(selected='B000000001,B000000009'),
                   dict(selected=ASINS, market='amazon.de'),
                   dict(selected=ASINS, max_calls=2),
                   dict(selected=ASINS, max_calls=5),
                   dict(selected=ASINS, auth_mode='env-api-key')]
        for params in invalid:
            with self.subTest(params=params), self.assertRaises(Failure):
                workflow_plan(resume=self.first, **params)
        for source, context in [(False, None), (True, AuthContext('browser-account', 'https://other.invalid', 'fake'))]:
            engine = executor('browser-account', 'complete', 4)
            if context:
                engine.context = context
            with self.assertRaises(Failure):
                compare(engine, self.root / 'rejected', resume=self.first, selected=ASINS,
                        mock=source, allow_paid=not source)
            self.assertEqual(engine.transport.calls, [])
            self.assertFalse((self.root / 'rejected').exists())

    def test_hash_damage_and_semantic_tampering_are_rejected(self):
        bad = self.root / 'bad'
        shutil.copytree(self.first, bad)
        (bad / 'candidates.json').write_text('[]')
        with self.assertRaises(Failure):
            workflow_plan(resume=bad, selected=ASINS)
        mutations = [('candidates.json', lambda value: value.clear()),
                     ('plan.json', lambda value: value.update(marketplace='amazon.de')),
                     ('request-1.json', lambda value: value.update(endpoint='/other')),
                     ('request-1.json', lambda value: value.update(params={'keyword': 'changed', 'amazonDomain': 'amazon.com'})),
                     ('result.json', lambda value: value['budget'].update(requestsSent=0)),
                     ('result.json', lambda value: value.update(status='FAILED'))]
        for index, (name, mutate) in enumerate(mutations):
            folder = self.root / str(index)
            shutil.copytree(self.first, folder)
            rewrite(folder, name, mutate)
            with self.subTest(name=name), self.assertRaises(Failure):
                workflow_plan(resume=folder, selected=ASINS)

    def test_manifest_rejects_paths_duplicate_keys_versions_and_oversize(self):
        manifest = self.first / 'manifest.json'
        original = manifest.read_bytes()
        for value in [dict(schemaVersion='nexscope.evidence.v1', files={'../secret.json': '0' * 64}),
                      dict(schemaVersion='unknown', files={'plan.json': '0' * 64}),
                      dict(schemaVersion='nexscope.evidence.v1', files={'C:/secret.json': '0' * 64})]:
            manifest.write_text(json.dumps(value))
            with self.assertRaises(Failure):
                read_bundle(self.first)
        for raw in [b'{"files":{},"files":{}}', b' ' * 65537]:
            manifest.write_bytes(raw)
            with self.assertRaises(Failure):
                read_bundle(self.first)
        manifest.write_bytes(original)

    def test_linked_evidence_is_rejected(self):
        target = self.root / 'outside.json'
        target.write_bytes((self.first / 'request-1.json').read_bytes())
        (self.first / 'request-1.json').unlink()
        try:
            (self.first / 'request-1.json').symlink_to(target)
        except OSError:
            self.skipTest('OS does not permit unprivileged symlinks')
        with self.assertRaises(Failure):
            read_bundle(self.first)

    def test_resume_dry_run_never_loads_credentials_or_transport(self):
        args = ['nexscope', 'workflow', 'compare', '--resume', str(self.first),
                '--select-asins', ASINS, '--mock', 'complete', '--dry-run']
        with patch('sys.argv', args), patch('nexscope_cli.core.remote.engine_for', side_effect=AssertionError), \
                patch('nexscope_cli.main.Client', side_effect=AssertionError), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 0)
        plan = json.loads(output.getvalue())
        self.assertEqual((plan['maximumRequests'], plan['requestsSent'], plan['newRequests']), (3, 1, 2))
        self.assertTrue(plan['importedSearch']['historical'])
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_failed_resume_is_not_replayable_or_overwritable(self):
        folder = self.root / 'failed'
        engine = executor('browser-account', 'timeout', 4)
        result = compare(engine, folder, resume=self.first, selected=ASINS, mock=True)
        self.assertEqual(result['status'], 'INSUFFICIENT_DATA')
        self.assertEqual(result['budget']['requestsSent'], 2)
        self.assertEqual(len(engine.transport.calls), 1)
        with self.assertRaises(Failure):
            workflow_plan(resume=folder, selected=ASINS)
        again = executor('browser-account', 'complete', 4)
        with self.assertRaises(FileExistsError):
            compare(again, folder, resume=self.first, selected=ASINS, mock=True)
        self.assertEqual(again.transport.calls, [])
        result = report(folder / 'dataset.json', self.root / 'failed.html')
        self.assertEqual(result['rows'], 0)

    def test_bad_output_parent_prevents_all_requests_without_fallback(self):
        engine = executor('browser-account', 'complete', 4)
        with self.assertRaises(FileNotFoundError):
            compare(engine, self.root / 'missing' / 'output', asins=ASINS, mock=True)
        self.assertEqual(engine.transport.calls, [])
        self.assertFalse((self.root / 'missing').exists())

    def test_resumed_report_is_portable_and_keeps_history(self):
        completed = self.root / 'complete'
        compare(executor('browser-account', 'complete', 4), completed, resume=self.first, selected=ASINS, mock=True)
        shared = self.root / 'shared'
        shutil.copytree(completed, shared)
        shutil.rmtree(completed)
        shutil.rmtree(self.first)
        result = report(shared / 'dataset.json', self.root / 'offline.html')
        final = Path(result['evidence'])
        self.assertEqual((final / 'request-1.json').read_bytes(), (shared / 'request-1.json').read_bytes())
        self.assertEqual(json.loads((final / 'dataset.json').read_text())['budget']['importedRequests'], 1)
        read_dataset(final / 'dataset.json')
        receipt = json.loads((final / 'report-input.json').read_text())
        self.assertEqual(receipt['inputSha256'], hashlib.sha256((shared / 'dataset.json').read_bytes()).hexdigest())

    def test_dataset_rejects_rehashed_product_evidence_and_metadata_changes(self):
        source = self.root / 'complete'
        compare(executor('browser-account', 'complete', 4), source, asins=ASINS, mock=True)
        mutations = [lambda value: value['products'][0].update(price=999),
                     lambda value: value['products'][0]['extra'].update(evidenceFile='../secret.json'),
                     lambda value: value.update(sourceType='remote'),
                     lambda value: value.update(schemaVersion=2),
                     lambda value: value.update(inputSha256='0' * 64),
                     lambda value: value['budget'].update(requestsSent=0),
                     lambda value: value.update(collectionStatus='PARTIAL')]
        for index, mutate in enumerate(mutations):
            folder = self.root / ('mutated' + str(index))
            shutil.copytree(source, folder)
            rewrite(folder, 'dataset.json', mutate)
            with self.subTest(index=index), self.assertRaises(DatasetError):
                report(folder / 'dataset.json', self.root / ('bad' + str(index) + '.html'))

    def test_dataset_rejects_changed_saved_plan_and_collection_result(self):
        source = self.root / 'complete'
        compare(executor('browser-account', 'complete', 4), source, asins=ASINS, mock=True)
        for name in ['plan.json', 'result.json']:
            folder = self.root / name
            shutil.copytree(source, folder)
            if name == 'result.json':
                rewrite(folder, name, lambda value: value.update(status='PARTIAL'))
            else:
                rewrite(folder, name, lambda value: value['steps'][0]['requests'][0].update(endpoint='/unregistered'))
                digest = hashlib.sha256((folder / name).read_bytes()).hexdigest()
                rewrite(folder, 'dataset.json', lambda value: value.update(inputSha256=digest))
            with self.subTest(name=name), self.assertRaises(DatasetError):
                read_dataset(folder / 'dataset.json')


if __name__ == '__main__':
    unittest.main()
