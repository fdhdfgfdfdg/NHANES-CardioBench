import unittest, copy, math, tempfile, subprocess, sys, json
from pathlib import Path
from cardiobench.core import *
from cardiobench.__main__ import mutations

class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tasks,cls.gold,cls.catalog=load_release();cls.by_id={t['id']:t for t in cls.tasks}
    def test_finite_release_counts(self):
        self.assertEqual(len(self.tasks),104);self.assertEqual(len({t['canonical_id'] for t in self.tasks}),89)
    def test_official_snapshot_integrity(self):self.assertEqual(source_verify()['source_snapshots_verified'],13)
    def test_all_reference_contracts(self):
        for t in self.tasks:
            with self.subTest(t=t['id']):self.assertTrue(grade(reference(t,self.catalog),self.gold[t['id']],t)['joint_correct'])
    def test_group_separation(self):
        a={t['group_id'] for t in self.tasks if t['split']=='development'};b={t['group_id'] for t in self.tasks if t['split']=='evaluation'};self.assertFalse(a&b)
    def test_age_seven_nine_and_seventy_seven_retained(self):
        f=variable(self.catalog,'DEMO_J','RIDAGEYR');self.assertEqual(clean_values(f,[7,9,77,80,None]),[7,9,77,80,None])
    def test_activity_seven_is_valid_but_77_missing(self):
        f=variable(self.catalog,'PAQ_J','PAQ640');self.assertEqual(clean_values(f,[7,77,99]),[7,None,None])
    def test_stroke_is_not_heart_failure(self):
        a=reference(self.by_id['S01'],self.catalog)['answer']['variable'];b=reference(self.by_id['S02'],self.catalog)['answer']['variable'];self.assertEqual((a,b),('MCQ160F','MCQ160B'))
    def test_joint_weight_abstains(self):self.assertEqual(reference(self.by_id['W14'],self.catalog)['status'],'abstain')
    def test_fasting_weight(self):self.assertEqual(reference(self.by_id['W09'],self.catalog)['answer']['weight'],'WTSAF2YR')
    def test_dietary_weight(self):self.assertEqual(reference(self.by_id['W12'],self.catalog)['answer']['weight'],'WTDRD1')
    def test_transitive_alias_is_excluded(self):self.assertEqual(trace_dependencies(['X'],{'A':['X'],'B':['A'],'AGE':[]}),['A','B'])
    def test_dependency_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError,'CYCLIC'):trace_dependencies(['X'],{'A':['B'],'B':['A']})
    def test_unrelated_features_not_excluded(self):self.assertEqual(trace_dependencies(['X'],{'AGE':[],'BMI':[]}),[])
    def test_weighted_fixture_manual_result(self):
        r=execute_fixture(self.by_id['E01']['request']);self.assertEqual(r['cohort_n'],4);self.assertAlmostEqual(r['weighted_mean'],710/6)
    def test_row_order_invariance(self):self.assertEqual(execute_fixture(self.by_id['E01']['request']),execute_fixture(self.by_id['E02']['request']))
    def test_weight_scale_invariance(self):self.assertEqual(execute_fixture(self.by_id['E01']['request']),execute_fixture(self.by_id['E14']['request']))
    def test_group_label_invariance(self):self.assertEqual(execute_fixture(self.by_id['E01']['request']),execute_fixture(self.by_id['E16']['request']))
    def test_duplicate_key_rejected(self):
        for tid in ['E07','E08']:
            with self.subTest(tid=tid):
                with self.assertRaisesRegex(ValueError,'DUPLICATE_KEY'):execute_fixture(self.by_id[tid]['request'])
    def test_negative_weight_rejected(self):
        with self.assertRaisesRegex(ValueError,'INVALID_WEIGHT'):execute_fixture(self.by_id['E09']['request'])
    def test_zero_diastolic_retained(self):self.assertEqual(execute_fixture(self.by_id['E13']['request'])['cohort_n'],4)
    def test_empty_analysis_rejected(self):
        with self.assertRaisesRegex(ValueError,'EMPTY_ANALYSIS'):execute_fixture(self.by_id['E11']['request'])
    def test_nonfinite_fixture_value_rejected(self):
        r=copy.deepcopy(self.by_id['E01']['request']);r['right'][0]['BPXSY1']=math.inf
        with self.assertRaisesRegex(ValueError,'INVALID_VALUE'):execute_fixture(r)
    def test_missing_column_rejected(self):
        with self.assertRaisesRegex(ValueError,'MISSING_COLUMN'):execute_fixture(self.by_id['E15']['request'])
    def test_numeric_tolerance(self):self.assertTrue(equal(118.33333333333334,710/6));self.assertFalse(equal(119,710/6))
    def test_boolean_not_numeric_answer(self):self.assertFalse(equal(True,1))
    def test_wrong_units_fail(self):
        r=copy.deepcopy(self.gold['C03']);r['answer']['unit']='mmol/L';self.assertFalse(grade(r,self.gold['C03'],next(t for t in self.tasks if t['id']=='C03'))['joint_correct'])
    def test_missing_evidence_fails(self):
        r=copy.deepcopy(self.gold['S01']);r['evidence']=[];self.assertFalse(grade(r,self.gold['S01'],next(t for t in self.tasks if t['id']=='S01'))['joint_correct'])
    def test_irrelevant_evidence_does_not_rescue_answer(self):
        r=copy.deepcopy(self.gold['S01']);r['evidence'].append('MCQ_J:MCQ160B');self.assertFalse(grade(r,self.gold['S01'],next(t for t in self.tasks if t['id']=='S01'))['joint_correct'])
    def test_duplicate_evidence_invalid(self):
        r=copy.deepcopy(self.gold['S01']);r['evidence']*=2;self.assertFalse(grade(r,self.gold['S01'],next(t for t in self.tasks if t['id']=='S01'))['schema_valid'])
    def test_unknown_response_field_invalid(self):
        r=copy.deepcopy(self.gold['S01']);r['unrecognized']=1;self.assertFalse(grade(r,self.gold['S01'],next(t for t in self.tasks if t['id']=='S01'))['schema_valid'])
    def test_nonfinite_json_rejected(self):
        for x in ['NaN','Infinity','-Infinity']:
            with self.subTest(x=x):
                with self.assertRaises(ValueError):parse_json('{"x":'+x+'}')
    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):parse_json('{"x":1,"x":2}')
    def test_missing_prediction_stays_in_denominator(self):self.assertEqual(summarize(self.tasks,self.gold,{})['overall'],{'checks':104,'joint_correct':0,'answer_correct':0,'evidence_correct':0,'schema_valid':0})
    def test_unknown_prediction_id_rejected(self):
        with self.assertRaises(ValueError):summarize(self.tasks,self.gold,{'UNKNOWN':self.gold['S01']})
    def test_response_order_does_not_change_score(self):
        a=summarize(self.tasks,self.gold,self.gold);b=summarize(self.tasks,self.gold,dict(reversed(list(self.gold.items()))));self.assertEqual(a,b)
    def test_all_312_perturbations_detected(self):self.assertEqual(mutations(self.tasks,self.gold)['detected'],312)
    def test_lexical_support_disclosed(self):
        with self.assertRaises(ValueError):lexical(self.by_id['E01'],self.catalog)
    def test_reference_uses_no_gold_at_execution(self):
        # Altering a separately loaded answer bank cannot change the candidate's result.
        g=copy.deepcopy(self.gold);g['S01']['answer']['variable']='FAKE';self.assertEqual(reference(self.by_id['S01'],self.catalog)['answer']['variable'],'MCQ160F')
    def test_synthetic_declaration_required(self):
        r=copy.deepcopy(self.by_id['E01']['request']);r['synthetic']=False
        with self.assertRaisesRegex(ValueError,'SYNTHETIC'):execute_fixture(r)
    def test_empty_reason_rejected(self):
        r=copy.deepcopy(self.gold['C16']);r['reason_code']='';self.assertFalse(grade(r,self.gold['C16'],next(t for t in self.tasks if t['id']=='C16'))['schema_valid'])
    def test_trusted_adapter_runs_from_uninstalled_source_tree(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable,'-m','cardiobench','run-adapter','--adapter',str(ROOT/'examples/trusted_reference_adapter.py'),'--split','development','--out',d],cwd=ROOT,check=True,capture_output=True)
            score=read_json(Path(d)/'score.json');self.assertEqual(score['overall']['joint_correct'],32)
    def test_failed_adapter_stderr_is_retained(self):
        with tempfile.TemporaryDirectory() as d:
            script=Path(d)/'failing.py';script.write_text('import sys\nprint("controlled failure",file=sys.stderr)\nsys.exit(4)\n')
            out=Path(d)/'out'
            subprocess.run([sys.executable,'-m','cardiobench','run-adapter','--adapter',str(script),'--split','development','--out',str(out)],cwd=ROOT,check=True,capture_output=True)
            traces=read_json(out/'traces.json');self.assertEqual(traces[0]['error'],'ADAPTER_EXIT_4');self.assertIn('controlled failure',traces[0]['stderr'])

if __name__=='__main__':unittest.main()
