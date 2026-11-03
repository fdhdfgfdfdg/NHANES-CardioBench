"""0.4.5 audit regressions. Modified evidence is synthetic, never a release claim."""
from pathlib import Path
from types import SimpleNamespace
import copy,json,unittest,zipfile,csv,io,base64,hashlib
from cardiobench import __version__
from cardiobench.core import load_release,read_json,reference,execute_fixture,parse_json,INTEGER_LIMIT,convert_glucose_values
from cardiobench.contracts import validate_tasks,validate_task_response,candidate_contract
from cardiobench.runner import run_adapter,file_hash
from cardiobench.artifacts import verify_artifacts,validate_package,validate_release_hygiene,HISTORICAL_VERSIONS

class RoundElevenTests(unittest.TestCase):
 def setUp(self):
  from test_round8 import RoundEightTests
  RoundEightTests.setUpClass();self.f=RoundEightTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.tasks,self.gold,self.catalog=load_release()
 def bundle(self):return self.f.bundle()
 def change_paper(self,change,error='REPRODUCTION'):
  root=self.bundle();p=root/'validation/process_reproduction/paper_results.json';v=read_json(p);change(v);p.write_text(json.dumps(v))
  timing=root/'validation/process_timing.json';v=read_json(timing);v['paper_results_sha256']=file_hash(p);timing.write_text(json.dumps(v));self.f.refreeze(root)
  with self.assertRaisesRegex(ValueError,error):verify_artifacts(root,True)
 def test_context_score_corruption(self):self.change_paper(lambda p:p['context_lexical']['overall'].update(joint_correct=16))
 def test_family_score_corruption(self):self.change_paper(lambda p:p['reference']['families']['semantic'].update(joint_correct=0))
 def test_split_score_corruption(self):self.change_paper(lambda p:p['reference']['splits']['development'].update(joint_correct=0))
 def test_row_score_corruption(self):self.change_paper(lambda p:p['reference']['rows'][0].update(joint_correct=False))
 def test_context_comparison_corruption(self):self.change_paper(lambda p:p['context_comparison'][0].update(context_variable='WRONG'))
 def test_trace_corruption(self):self.change_paper(lambda p:p['lexical_traces'][0].update(retrieved='WRONG'))
 def test_historical_subset_corruption(self):self.change_paper(lambda p:p['legacy_reference']['overall'].update(joint_correct=0))
 def test_extension_subset_corruption(self):self.change_paper(lambda p:p['extension_reference']['overall'].update(joint_correct=0))
 def test_source_binding_corruption(self):self.change_paper(lambda p:p['runner_source_hashes'].clear())
 def test_negative_timing(self):self.change_paper(lambda p:p['timing'].update(warm_reference_median_seconds=-1))
 def test_inconsistent_timing_summary(self):self.change_paper(lambda p:p['timing'].update(warm_reference_median_seconds=0.2))
 def test_inconsistent_timing_repeats(self):self.change_paper(lambda p:p['timing'].update(warm_reference_repeats=29))
 def test_timing_raw_value_type(self):self.change_paper(lambda p:p['timing']['warm_reference_raw_seconds'].__setitem__(0,True))
 def test_missing_context_predictions(self):
  root=self.bundle();(root/'validation/process_reproduction/context_lexical_predictions.json').unlink();self.f.refreeze(root)
  with self.assertRaisesRegex(ValueError,'REQUIRED_DELIVERY'):verify_artifacts(root,True)
 def test_context_prediction_corruption(self):
  root=self.bundle();p=root/'validation/process_reproduction/context_lexical_predictions.json';p.write_text('{}');self.f.refreeze(root)
  with self.assertRaisesRegex(ValueError,'PREDICTIONS_MISMATCH'):verify_artifacts(root,True)
 def test_csv_corruption(self):
  root=self.bundle();(root/'validation/process_reproduction/check_results.csv').write_text('incorrect');self.f.refreeze(root)
  with self.assertRaisesRegex(ValueError,'CSV_MISMATCH'):verify_artifacts(root,True)
 def test_unknown_paper_field(self):self.change_paper(lambda p:p.update(unvalidated_result=100))
 def test_invalid_wheel_filenames(self):
  root=self.bundle();original=next((root/'packages').glob('*.whl'))
  for name in ['current.whl','other-'+__version__+'-py3-none-any.whl','nhanes_cardiobench-'+__version__+'-cp312-none-any.whl']:
   p=root/name;p.write_bytes(original.read_bytes())
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'FILENAME_MISMATCH'):validate_package(p,root)
 def test_wrong_dist_info_directory(self):
  root=self.bundle();path=next((root/'packages').glob('*.whl'))
  with zipfile.ZipFile(path) as z:files={n.replace('nhanes_cardiobench-'+__version__+'.dist-info','other-'+__version__+'.dist-info'):z.read(n) for n in z.namelist()}
  with zipfile.ZipFile(path,'w') as z:
   for n,b in files.items():z.writestr(n,b)
  with self.assertRaisesRegex(ValueError,'DIST_INFO_MISMATCH'):validate_package(path,root)
 def test_wrong_python_requirement(self):
  root=self.bundle();folder='nhanes_cardiobench-'+__version__+'.dist-info/'
  p=self.f.package(root,'wheel',changed=lambda m:m.__setitem__(folder+'METADATA',m[folder+'METADATA'].replace(b'>=3.10',b'>=99')))
  with self.assertRaisesRegex(ValueError,'REQUIREMENTS_MISMATCH'):validate_package(p,root)
 def test_unexpected_runtime_dependency(self):
  root=self.bundle();folder='nhanes_cardiobench-'+__version__+'.dist-info/'
  p=self.f.package(root,'wheel',changed=lambda m:m.__setitem__(folder+'METADATA',m[folder+'METADATA']+b'Requires-Dist: missing-dependency\n'))
  with self.assertRaisesRegex(ValueError,'REQUIREMENTS_MISMATCH'):validate_package(p,root)
 def test_current_and_unknown_version_residue(self):
  root=self.f.root
  for version in ['v'+__version__.replace('.','_'),'v99_0_0','v0_0_1']:
   p=root/'validation'/version/'run.lock';p.parent.mkdir(parents=True);p.write_text('synthetic')
   with self.subTest(version=version),self.assertRaisesRegex(ValueError,'TRANSIENT'):validate_release_hygiene(root)
   p.unlink()
 def test_registered_history_residue_is_retained(self):
  root=self.f.root
  for version in HISTORICAL_VERSIONS:
   p=root/'validation'/version/'run.lock';p.parent.mkdir(parents=True);p.write_text('archived')
  validate_release_hygiene(root)
 def test_reserved_task_names_preflight(self):
  for name in ['CON','nul','AUX','PRN','COM1','com9','LPT1','lpt9']:
   t=copy.deepcopy(self.tasks[0]);t['id']=name
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'RESERVED_TASK_ID'):validate_tasks([t],{name:self.gold[self.tasks[0]['id']]})
 def test_case_colliding_ids_before_outputs(self):
  ts=[dict(copy.deepcopy(self.tasks[0]),id=x) for x in ['Case','case']];g={t['id']:self.gold[self.tasks[0]['id']] for t in ts};out=self.f.root/'run'
  args=SimpleNamespace(timeout=1,stdout_limit=10000,stderr_limit=1000,max_cases=None,track='provided-context',out=str(out))
  with self.assertRaisesRegex(ValueError,'CASE_COLLIDING_TASK_ID'):run_adapter(args,ts,g,self.catalog)
  self.assertFalse(out.exists())
 def test_nondevice_ids_allowed(self):
  for name in ['CONTEXT','COM10','LPT10','normal-1']:
   t=dict(copy.deepcopy(self.tasks[0]),id=name);validate_tasks([t],{name:self.gold[self.tasks[0]['id']]})
 def test_integer_json_limit_and_boundary(self):
  for s in ['1'+'0'*5000,'-'+'1'+'0'*5000]:
   with self.assertRaisesRegex(ValueError,'INTEGER_LIMIT_EXCEEDED'):parse_json(s)
  self.assertEqual(parse_json('9'*4096),INTEGER_LIMIT-1)
 def test_task_integer_limit(self):
  t=copy.deepcopy(next(t for t in self.tasks if t['kind']=='coding' and t['request']['operation']=='convert_glucose'));t['request']['values']=[10**5000]
  with self.assertRaisesRegex(ValueError,'INTEGER_LIMIT_EXCEEDED'):validate_tasks([t],self.gold)
  r=reference(t,self.catalog);self.assertEqual(r['reason_code'],'INTEGER_LIMIT_EXCEEDED');validate_task_response(t,r)
 def fixture(self,power):
  t=copy.deepcopy(next(t for t in self.tasks if t['kind']=='execution' and self.gold[t['id']]['status']=='answer'));r=t['request'];k,w,a,v=[r[n] for n in ['key','weight_column','age_column','value_column']]
  r['left']=[{k:1,w:10**power,a:40},{k:2,w:10**power,a:40}];r['right']=[{k:1,v:100},{k:2,v:200}];r['minimum_age']=18;return t
 def test_over_limit_weight_rejection_has_valid_reason(self):
  t=self.fixture(5000);r=reference(t,self.catalog);self.assertEqual(r['reason_code'],'INTEGER_LIMIT_EXCEEDED');validate_task_response(t,r)
 def test_supported_large_weights_retain_finite_mean(self):self.assertEqual(execute_fixture(self.fixture(400)['request'])['weighted_mean'],150.0)
 def test_contract_reason_and_bound_are_exported(self):
  c=candidate_contract(self.tasks[0]);self.assertEqual(c['contract_version'],'1.4');self.assertEqual(c['protocol_constraints']['maximum_integer_decimal_digits'],4096);self.assertIn('conversion',c['reason_codes']['NONFINITE_RESULT'])
if __name__=='__main__':unittest.main()
