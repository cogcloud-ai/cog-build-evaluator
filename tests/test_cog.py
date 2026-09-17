import copy
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import cog_core as core
import task_logic as logic

def read(path):
    return json.loads((ROOT / path).read_text())

class SharedChecks(unittest.TestCase):
    def setUp(self):
        self.bundle = read('examples/sample-bundle.json')
        self.payload = read('context/output-example.json')

    def test_examples_agree(self):
        self.assertEqual(core.validate_input(self.bundle), [])
        self.assertEqual(core.validate_output(self.payload, self.bundle), [])

    def test_fixtures_have_valid_inputs(self):
        manifest = yaml.safe_load((ROOT / 'cog.yaml').read_text())
        self.assertGreaterEqual(len(manifest['evaluation']['fixtures']), 4)
        for path in manifest['evaluation']['fixtures']:
            fixture = yaml.safe_load((ROOT / path).read_text())
            self.assertEqual(core.validate_input(read(fixture['bundle'])), [], path)

    def test_bad_shapes_report_problems(self):
        for key in self.bundle:
            for bad in [None, 17, [], {'bad': []}]:
                bundle = copy.deepcopy(self.bundle); bundle[key] = bad
                if bundle != self.bundle:
                    self.assertTrue(core.validate_input(bundle), (key, bad))
        for key in self.payload:
            bad = copy.deepcopy(self.payload); bad[key] = 17
            self.assertTrue(core.validate_output(bad, self.bundle), key)

    def test_invocation_envelope_and_prompt(self):
        body = {'model': core.MODEL, 'choices': [{'message': {'content': json.dumps(self.payload)}}]}
        response = io.BytesIO(json.dumps(body).encode())
        with patch.object(core, 'health', return_value=(True, 'mock')), patch.object(core.urllib.request, 'urlopen', return_value=response) as call:
            result = core.invoke(self.bundle)
        self.assertTrue(result['ok'])
        self.assertEqual(result['envelope'], 1)
        self.assertEqual(result['payload'], self.payload)
        self.assertEqual(result['problems'], [])
        self.assertEqual(result['binding']['model_identity'], 'verified')
        sent = json.loads(call.call_args.args[0].data)
        self.assertIn(self.bundle['operation'], sent['messages'][1]['content'])

    def test_problem_envelope_is_not_silent_success(self):
        bad = copy.deepcopy(self.payload); bad['classification'] = 'pass' if ROOT.name == 'cog-author' else 'revise'
        body = {'model': core.MODEL, 'choices': [{'message': {'content': json.dumps(bad)}}]}
        with patch.object(core, 'health', return_value=(True, 'mock')), patch.object(core.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(body).encode())):
            result = core.invoke(self.bundle)
        self.assertTrue(result['ok'])
        self.assertTrue(result['problems'])

    def test_invalid_input_never_calls_model(self):
        with patch.object(core.urllib.request, 'urlopen') as call:
            result = core.invoke({})
        self.assertFalse(result['ok'])
        call.assert_not_called()

    def test_abstention_requires_reason(self):
        p = copy.deepcopy(self.payload); p.update(abstained=True, classification='abstained', reason='')
        self.assertTrue(core.validate_output(p, self.bundle))

class EvaluationChecks(unittest.TestCase):
    def setUp(self):
        self.bundle = read('examples/sample-bundle.json')
        self.bundle.update(operation='review', files=[{'path': 'task.py', 'content': 'return wrong_answer'}])
        self.payload = read('context/output-example.json')
        self.payload['classification'] = 'insufficient_evidence'

    def evidence(self, status='passed', kind='execution'):
        self.bundle['evidence'] = [{'id': c['id'], 'criterion_id': c['id'], 'candidate_sha256': logic.candidate_sha256(self.bundle), 'kind': kind, 'status': status, 'text': 'Observed exact expected result.'} for c in self.bundle['contract']['acceptance_criteria']]
        for a in self.payload['assessments']:
            a.update(status='pass', evidence_ids=[a['criterion_id']], evidence_quote='exact expected result')
        self.payload['classification'] = 'pass'

    def test_missing_evidence_remains_not_tested(self):
        self.assertEqual(core.validate_output(self.payload, self.bundle), [])
        self.payload['classification'] = 'pass'
        self.assertTrue(core.validate_output(self.payload, self.bundle))

    def test_candidate_bound_execution_can_pass(self):
        self.evidence()
        self.assertEqual(core.validate_input(self.bundle), [])
        self.assertEqual(core.validate_output(self.payload, self.bundle), [])

    def test_stale_evidence_refused(self):
        self.evidence(); self.bundle['files'][0]['content'] += ' changed'
        self.assertTrue(core.validate_input(self.bundle))

    def test_inspection_cannot_pass(self):
        self.evidence(kind='inspection')
        self.assertTrue(core.validate_output(self.payload, self.bundle))

    def test_failed_execution_cannot_be_hidden(self):
        self.evidence(status='failed')
        self.assertTrue(core.validate_output(self.payload, self.bundle))
        self.payload['classification'] = 'revise'
        for a in self.payload['assessments']: a['status'] = 'fail'
        self.assertEqual(core.validate_output(self.payload, self.bundle), [])

    def test_reviewer_can_disagree_with_passing_test(self):
        self.evidence(); self.payload['assessments'][0]['status'] = 'fail'; self.payload['classification'] = 'revise'
        self.assertEqual(core.validate_output(self.payload, self.bundle), [])

    def test_invented_and_wrong_criterion_evidence(self):
        self.evidence(); self.payload['assessments'][0]['evidence_quote'] = 'never observed'
        self.assertTrue(core.validate_output(self.payload, self.bundle))
        self.payload['assessments'][0]['evidence_quote'] = 'exact expected result'
        self.payload['assessments'][0]['evidence_ids'] = [self.payload['assessments'][1]['criterion_id']]
        self.assertTrue(core.validate_output(self.payload, self.bundle))

    def test_source_findings_must_be_grounded(self):
        self.payload['findings'] = [{'severity':'error', 'path':'task.py', 'quote':'wrong_answer', 'detail':'Returns a constant rather than a task result.'}]
        self.payload['classification'] = 'revise'
        self.assertEqual(core.validate_output(self.payload, self.bundle), [])
        self.payload['findings'][0]['quote'] = 'invented'
        self.assertTrue(core.validate_output(self.payload, self.bundle))

    def test_no_missing_or_duplicate_criteria(self):
        self.payload['assessments'][1] = self.payload['assessments'][0]
        self.assertTrue(core.validate_output(self.payload, self.bundle))

    def test_plan_rejects_procedure_instead_of_candidate_input(self):
        self.bundle['operation'] = 'plan'
        self.payload['classification'] = 'planned'
        self.payload['test_cases'][0]['input'] = {'construction': 'Generate a matrix of test inputs.'}
        self.assertTrue(any('one concrete schema-valid candidate bundle' in p['detail'] for p in core.validate_output(self.payload, self.bundle)))

    def test_case_schema_never_fetches_remote_refs(self):
        self.bundle['contract']['input_schema'] = {'$ref': 'https://example.com/schema'}
        self.assertTrue(any('local references' in p['detail'] for p in core.validate_output(self.payload, self.bundle)))

    def test_plan_cannot_claim_execution(self):
        self.evidence(); self.bundle['operation'] = 'plan'; self.payload['classification'] = 'planned'
        self.assertTrue(core.validate_output(self.payload, self.bundle))

    def test_fingerprint_is_order_independent_but_contract_sensitive(self):
        self.bundle['files'].append({'path': 'b.py', 'content': 'b'})
        old = logic.candidate_sha256(self.bundle)
        self.bundle['files'].reverse()
        self.assertEqual(old, logic.candidate_sha256(self.bundle))
        self.bundle['contract']['purpose'] += ' changed'
        self.assertNotEqual(old, logic.candidate_sha256(self.bundle))
