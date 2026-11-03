"""0.4.8 regressions for controlled errors and one operation rule."""
from pathlib import Path
from types import SimpleNamespace
import copy,json,shutil,subprocess,sys,unittest
from cardiobench.core import ROOT,load_release,read_json,summarize
from cardiobench.contracts import validate_tasks,candidate_contract,response_descriptor
from cardiobench.runner import binding,run_adapter
from cardiobench.binding_contract import validate_binding
from cardiobench.reproduction_evidence import validate_timing
from cardiobench.artifacts import verify_artifacts,sha

class RoundFourteenTests(unittest.TestCase):
 def setUp(self):
  from test_round8 import RoundEightTests
  RoundEightTests.setUpClass();self.f=RoundEightTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.tasks,self.gold,self.catalog=load_release()
 def args(self):
  return SimpleNamespace(adapter=str(ROOT/'examples/trusted_reference_adapter.py'),prompt_file=None,disclosure=None,track='provided-context',timeout=30,stdout_limit=1000000,stderr_limit=64000,max_cases=None,retry_failed=False,resume=False,out=str(self.f.root/'run'))
 def noncoding(self):return [copy.deepcopy(next(t for t in self.tasks if t['kind']==kind)) for kind in ('semantic','weights','leakage','execution')]
 def invalid_reports(self,name):
  r=self.f.bundle();p=r/'validation'/name
  for value in ([],None,'text',7,1.25,True):
   with self.subTest(report=name,value=value):
    p.write_text(json.dumps(value));self.f.refreeze(r)
    with self.assertRaisesRegex(ValueError,'INSTALLATION_EVIDENCE_MUST_BE_OBJECT'):verify_artifacts(r,True)
 def test_wheel_report_nonobjects_are_controlled(self):self.invalid_reports('installation.json')
 def test_sdist_report_nonobjects_are_controlled(self):self.invalid_reports('sdist_build.json')
 def test_valid_object_reports_remain_accepted(self):self.assertEqual(verify_artifacts(self.f.bundle(),True)['status'],'verified')
 def test_installation_error_from_actual_release_cli(self):
  from delivery_fixture import populate
  r=self.f.copy_core();(r/'packages').mkdir();self.f.package(r,'wheel');self.f.package(r,'sdist');populate(r,self.tasks,self.gold,self.catalog)
  for name,value in (('installation.json',[]),('sdist_build.json',None)):
   p=r/'validation'/name;original=p.read_bytes();p.write_text(json.dumps(value));self.f.refreeze(r)
   done=subprocess.run([sys.executable,'tools/check_release.py'],cwd=r,text=True,capture_output=True)
   with self.subTest(report=name):
    self.assertEqual(done.returncode,2,done.stderr);self.assertIn('INSTALLATION_EVIDENCE_MUST_BE_OBJECT: '+name,done.stderr);self.assertNotIn('Traceback',done.stderr);self.assertFalse(done.stdout)
   p.write_bytes(original)
 def timing(self):return copy.deepcopy(read_json(ROOT/'results/paper/paper_results.json')['timing'])
 def test_all_scalar_timing_overflows_are_controlled(self):
  for key in ('reference_first_seconds','lexical_seconds','context_lexical_seconds','warm_reference_median_seconds','warm_reference_min_seconds','warm_reference_max_seconds'):
   value=self.timing();value[key]=10**400
   with self.subTest(field=key),self.assertRaisesRegex(ValueError,'REPRODUCTION_TIMING_INVALID'):validate_timing(value)
 def test_each_raw_timing_position_overflow_is_controlled(self):
  for i in range(30):
   value=self.timing();value['warm_reference_raw_seconds'][i]=10**400
   with self.subTest(index=i),self.assertRaisesRegex(ValueError,'REPRODUCTION_TIMING_INVALID'):validate_timing(value)
 def test_invalid_timing_numeric_classes_are_controlled(self):
  for number in (True,False,0,-1,-10**400,float('nan'),float('inf'),float('-inf'),'1',None):
   value=self.timing();value['reference_first_seconds']=number
   with self.subTest(value=str(number)),self.assertRaisesRegex(ValueError,'REPRODUCTION_TIMING_INVALID'):validate_timing(value)
 def test_valid_integer_and_float_timings_are_accepted(self):
  for number in (1,0.125,1e-300,1e300):
   value=self.timing();value['reference_first_seconds']=number;validate_timing(value)
 def test_primary_timing_overflow_from_actual_core_cli(self):
  r=self.f.copy_core();out=self.f.root/'reproduced'
  done=subprocess.run([sys.executable,'-m','cardiobench','reproduce','--out',str(out)],cwd=r,text=True,capture_output=True)
  self.assertEqual(done.returncode,0,done.stderr)
  for p in out.iterdir():shutil.copy2(p,r/'results/paper'/p.name)
  p=r/'results/paper/paper_results.json';value=read_json(p);value['timing']['reference_first_seconds']=10**400;p.write_text(json.dumps(value))
  m=read_json(r/'MANIFEST_SHA256.json')
  for name in m['files']:m['files'][name]=sha(r/name)
  (r/'MANIFEST_SHA256.json').write_text(json.dumps(m))
  done=subprocess.run([sys.executable,'tools/check_release.py','--core-only'],cwd=r,text=True,capture_output=True)
  self.assertEqual(done.returncode,2,done.stderr);self.assertIn('REPRODUCTION_TIMING_INVALID',done.stderr);self.assertNotIn('Traceback',done.stderr);self.assertFalse(done.stdout)
 def test_timeout_overflow_fails_before_output(self):
  args=self.args();args.timeout=10**400
  with self.assertRaisesRegex(ValueError,'Timeout must be positive and finite'):run_adapter(args,self.tasks[:1],self.gold,self.catalog)
  self.assertFalse(Path(args.out).exists())
 def test_noncoding_operation_rejected_by_preflight(self):
  for t in self.noncoding():
   for value in ('semantic_lookup','unit',0,False,[],{}):
    t['request']['operation']=value
    with self.subTest(kind=t['kind'],value=value),self.assertRaisesRegex(ValueError,'INVALID_TASK_OPERATION'):validate_tasks([t],self.gold)
 def test_noncoding_operation_rejected_by_scoring(self):
  for t in self.noncoding():
   t['request']['operation']='semantic_lookup'
   with self.subTest(kind=t['kind']),self.assertRaisesRegex(ValueError,'INVALID_TASK_OPERATION'):summarize([t],self.gold,{t['id']:self.gold[t['id']]})
 def test_noncoding_operation_rejected_by_response_contract(self):
  for t in self.noncoding():
   t['request']['operation']='unit'
   with self.subTest(kind=t['kind']),self.assertRaisesRegex(ValueError,'INVALID_TASK_OPERATION'):candidate_contract(t)
 def test_invalid_operation_run_creates_no_output(self):
  for t in self.noncoding():
   args=self.args();t['request']['operation']='unit'
   with self.subTest(kind=t['kind']),self.assertRaisesRegex(ValueError,'INVALID_TASK_OPERATION'):run_adapter(args,[t],self.gold,self.catalog)
   self.assertFalse(Path(args.out).exists())
 def test_invalid_operation_direct_binding_rejected(self):
  for t in self.noncoding():
   t['request']['operation']='unit'
   with self.subTest(kind=t['kind']),self.assertRaisesRegex(ValueError,'INVALID_TASK_OPERATION'):binding(self.args(),[t],self.catalog,self.gold)
 def test_invalid_archived_operation_rejected(self):
  for t in self.noncoding():
   value,_=binding(self.args(),[t],self.catalog,self.gold);value['response_task_types'][t['id']]['request']['operation']='unit'
   with self.subTest(kind=t['kind']),self.assertRaisesRegex(ValueError,'INVALID_RUN_BINDING'):validate_binding(value)
 def test_null_and_omitted_noncoding_operation_agree(self):
  for t in self.noncoding():
   for explicit in (False,True):
    if explicit:t['request']['operation']=None
    else:t['request'].pop('operation',None)
    validate_tasks([t],self.gold);candidate_contract(t)
    self.assertEqual(summarize([t],self.gold,{t['id']:self.gold[t['id']]})['overall']['joint_correct'],1)
    value,_=binding(self.args(),[t],self.catalog,self.gold);validate_binding(value,[t]);self.assertIsNone(value['response_task_types'][t['id']]['request']['operation'])
 def test_coding_operations_agree_across_entrypoints(self):
  for op in ('unit','clean','convert_glucose'):
   t=copy.deepcopy(next(t for t in self.tasks if t['kind']=='coding' and t['request']['operation']==op));validate_tasks([t],self.gold);candidate_contract(t)
   value,_=binding(self.args(),[t],self.catalog,self.gold);validate_binding(value,[t]);self.assertEqual(response_descriptor(t)['request']['operation'],op)
 def test_unknown_coding_operation_rejected_consistently(self):
  t=copy.deepcopy(next(t for t in self.tasks if t['kind']=='coding'));t['request']['operation']='unknown'
  for call in (lambda:validate_tasks([t],self.gold),lambda:candidate_contract(t),lambda:binding(self.args(),[t],self.catalog,self.gold)):
   with self.assertRaisesRegex(ValueError,'INVALID_TASK_OPERATION'):call()
 def test_unrelated_request_metadata_remains_allowed(self):
  t=self.noncoding()[0];t['request']['note']='custom metadata';validate_tasks([t],self.gold);candidate_contract(t)
  value,_=binding(self.args(),[t],self.catalog,self.gold);validate_binding(value,[t])
