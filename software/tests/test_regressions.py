"""Regression cases for the first correctness audit, not new benchmark tasks."""
import copy, json, math, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import cardiobench.core as c

class CorrectnessRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks,cls.gold,cls.catalog=c.load_release()
        cls.fixture=next(t['request'] for t in cls.tasks if t['id']=='E01')
    def fixture_error(self,edit,reason):
        r=copy.deepcopy(self.fixture);edit(r)
        with self.assertRaisesRegex(ValueError,reason):c.execute_fixture(r)
    def test_float_missing_codes(self):
        f=c.variable(self.catalog,'MCQ_J','MCQ160F')
        self.assertEqual(c.clean_values(f,[7,7.0,9,9.0,'7.0']),[None]*5)
    def test_nonmissing_numeric_representations_preserved(self):
        f=c.variable(self.catalog,'DEMO_J','RIDAGEYR')
        self.assertEqual(c.clean_values(f,[7.0,9,77,'80']),[7.0,9,77,'80'])
    def test_bool_code_rejected(self):
        with self.assertRaisesRegex(ValueError,'INVALID_CODE'):c.clean_values(c.variable(self.catalog,'MCQ_J','MCQ160F'),[True])
    def test_json_exponent_overflow(self):
        for raw in ['{"x":1e400}','{"a":[-1e400]}']:
            with self.assertRaisesRegex(ValueError,'NONFINITE'):c.parse_json(raw)
    def test_fractional_count_not_accepted(self):
        r=copy.deepcopy(self.gold['E01']);r['answer']['cohort_n']=4.00000001
        g=c.grade(r,self.gold['E01'],next(t for t in self.tasks if t['id']=='E01'));self.assertFalse(g['joint_correct']);self.assertFalse(g['schema_valid'])
        self.assertIn('cohort_n',g['error'])
    def test_integer_counts_exact(self):self.assertFalse(c.equal(4.0,4));self.assertFalse(c.equal(4000000001,4000000000))
    def test_continuous_tolerance_retained(self):self.assertTrue(c.equal(118.333333334,118.33333333333333))
    def test_empty_answer_schema_invalid(self):
        r=copy.deepcopy(self.gold['S01']);r['answer']={}
        self.assertFalse(c.grade(r,self.gold['S01'],next(t for t in self.tasks if t['id']=='S01'))['schema_valid'])
    def test_unhashable_status(self):
        r=copy.deepcopy(self.gold['S01']);r['status']=[]
        self.assertFalse(c.grade(r,self.gold['S01'],next(t for t in self.tasks if t['id']=='S01'))['schema_valid'])
    def test_whitespace_reason_invalid(self):
        with self.assertRaises(ValueError):c.validate_response(c.response('reject',reason=' '))
    def test_nonanswer_payload_rejected(self):
        with self.assertRaises(ValueError):c.validate_response(c.response('reject',answer={'x':1},reason='INVALID'))
    def test_null_key_rejected(self):self.fixture_error(lambda r:r['left'][0].update(SEQN=None),'INVALID_KEY')
    def test_bool_key_rejected(self):self.fixture_error(lambda r:r['left'][0].update(SEQN=True),'INVALID_KEY')
    def test_string_key_rejected(self):self.fixture_error(lambda r:r['left'][0].update(SEQN='101'),'INVALID_KEY')
    def test_missing_key_rejected(self):self.fixture_error(lambda r:r['left'][0].pop('SEQN'),'MISSING_COLUMN')
    def test_bool_threshold_rejected(self):self.fixture_error(lambda r:r.update(minimum_age=True),'INVALID_MINIMUM_AGE')
    def test_nonfinite_threshold_rejected(self):self.fixture_error(lambda r:r.update(minimum_age=math.inf),'INVALID_MINIMUM_AGE')
    def test_missing_threshold_rejected(self):self.fixture_error(lambda r:r.pop('minimum_age'),'MISSING_FIELD')
    def test_invalid_rows_rejected(self):self.fixture_error(lambda r:r.update(right=[None]),'INVALID_ROWS')
    def test_unmatched_invalid_value_rejected(self):self.fixture_error(lambda r:r['right'].append({'SEQN':999,'BPXSY1':math.inf}),'INVALID_VALUE')
    def test_finite_large_products_do_not_overflow(self):
        r=copy.deepcopy(self.fixture);r['left'][0]['WTMEC2YR']=1e308;r['right'][0]['BPXSY1']=1e308
        self.assertEqual(c.execute_fixture(r)['weighted_mean'],1e308)
    def test_unrepresentable_mean_rejected(self):
        self.fixture_error(lambda r:r['right'][0].update(BPXSY1=10**400),'NONFINITE_RESULT')
    def test_manifest_detects_gold_edit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'cardiobench/data').mkdir(parents=True)
            p=root/'cardiobench/data/gold.json';p.write_text('{}')
            import hashlib
            names={'cardiobench/data/gold.json','README.md','LICENSE','CITATION.cff','codemeta.json','requirements.txt','requirements-build.txt','environment.lock.json','.python-version','.github/workflows/check.yml','pyproject.toml','setup.py','MANIFEST.in','.gitattributes'}
            for name in names-{'cardiobench/data/gold.json'}:
                q=root/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text('')
            files={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
            (root/'MANIFEST_SHA256.json').write_text(json.dumps({'version':c.__version__,'algorithm':'sha256','files':files}))
            with patch.object(c,'ROOT',root):
                c.distribution_verify();p.write_text('{"modified":true}')
                with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):c.distribution_verify()
    def test_malformed_adapter_does_not_abort_batch(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);adapter=p/'adapter.py'
            adapter.write_text('import json\nprint(json.dumps({"status":[],"answer":{},"evidence":[],"reason_code":None}))\n')
            run=subprocess.run([sys.executable,'-m','cardiobench','run-adapter','--adapter',str(adapter),'--split','development','--out',str(p/'out')],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            report=json.loads((p/'out/score.json').read_text())
            self.assertEqual(report['overall']['checks'],32);self.assertEqual(report['overall']['joint_correct'],0)
            self.assertEqual(len(json.loads((p/'out/traces.json').read_text())),32)
    def test_nonfinite_timeout_rejected(self):
        run=subprocess.run([sys.executable,'-m','cardiobench','run-adapter','--adapter','examples/trusted_reference_adapter.py','--timeout','nan','--out','unused'],capture_output=True,text=True)
        self.assertEqual(run.returncode,2);self.assertIn('Timeout',run.stderr)
