"""Regression coverage for evidence errors, execution drift and API boundaries."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy,json,os,tempfile,unittest
from cardiobench.core import load_release,read_json
from cardiobench.runner import run_adapter,validate_state,digest,capture
from cardiobench.__main__ import dump

class RoundFiveTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.tasks,cls.gold,cls.catalog=load_release()
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name);self.adapter=self.root/'adapter.py'
  self.adapter.write_text('import json,sys\nx=json.load(sys.stdin)\nprint(json.dumps('+repr(self.gold)+'[x["task"]["id"]]))')
  self.args=SimpleNamespace(adapter=str(self.adapter),out=str(self.root/'out'),timeout=2.,track='provided-context',resume=False,retry_failed=False,max_cases=None,prompt_file=None,disclosure=None,stdout_limit=10000,stderr_limit=10000,dependency_file=[],dependency_package=[],environment_file=None,adapter_cwd=None)
 def runone(self,tasks=None,gold=None):return run_adapter(self.args,self.tasks[:1] if tasks is None else tasks,self.gold if gold is None else gold,self.catalog)
 def fail_state(self,error):
  self.runone();s=read_json(self.root/'out/checkpoint.json')['state'];s['records'][0]['attempts'][0].update(error=error,response=None);return s
 def validate(self,s):return validate_state({'state':s,'sha256':digest(s)},s['binding'])
 def test_false_exit_failure_rejected(self):
  with self.assertRaisesRegex(ValueError,'FAILURE_CAPTURE'):self.validate(self.fail_state('ADAPTER_EXIT_9'))
 def test_false_parse_failure_rejected(self):
  with self.assertRaisesRegex(ValueError,'FAILURE_CAPTURE'):self.validate(self.fail_state('ADAPTER_RESPONSE_ERROR: forged'))
 def test_false_utf8_failure_rejected(self):
  with self.assertRaisesRegex(ValueError,'FAILURE_CAPTURE'):self.validate(self.fail_state('ADAPTER_INVALID_UTF8'))
 def test_false_output_limit_rejected(self):
  with self.assertRaisesRegex(ValueError,'OUTPUT_LIMIT_EVIDENCE'):self.validate(self.fail_state('ADAPTER_OUTPUT_LIMIT'))
 def test_unknown_failure_rejected(self):
  with self.assertRaisesRegex(ValueError,'FAILURE_CAPTURE'):self.validate(self.fail_state('arbitrary failure'))
 def test_real_exit_failure_resume(self):
  self.adapter.write_text('import sys\nsys.exit(9)');self.runone();self.args.resume=True
  self.assertEqual(self.runone()['run']['error_counts'],{'ADAPTER_EXIT_9':1})
 def test_real_parse_failure_resume(self):
  self.adapter.write_text('print("not JSON")');self.runone();self.args.resume=True
  self.assertEqual(self.runone()['run']['failed_cases'],1)
 def test_real_utf8_failure_resume(self):
  self.adapter.write_text('import sys\nsys.stdout.buffer.write(b"\\xff")');self.runone();self.args.resume=True
  self.assertEqual(self.runone()['run']['error_counts'],{'ADAPTER_INVALID_UTF8':1})
 def test_launch_failure_cannot_contain_output(self):
  with patch('cardiobench.runner.capture',side_effect=OSError('launch')):self.runone()
  s=read_json(self.root/'out/checkpoint.json')['state'];s['records'][0]['attempts'][0]['stdout']='impossible output'
  with self.assertRaisesRegex(ValueError,'INVALID_LAUNCH'):self.validate(s)
 def test_unsafe_task_ids_rejected_before_writes(self):
  for tid in ['../../escaped','/tmp/escaped','a/b','a\\b','..','',42]:
   with self.subTest(tid=tid):
    t=copy.deepcopy(self.tasks[:1]);t[0]['id']=tid
    with self.assertRaisesRegex(ValueError,'INVALID_TASK_ID'):self.runone(t,{tid:self.gold[self.tasks[0]['id']]})
    self.assertFalse(Path(self.args.out).exists())
 def test_duplicate_task_ids_rejected(self):
  with self.assertRaisesRegex(ValueError,'DUPLICATE_TASK_ID'):self.runone([self.tasks[0],self.tasks[0]])
  self.assertFalse(Path(self.args.out).exists())
 def test_missing_gold_rejected_before_writes(self):
  with self.assertRaisesRegex(ValueError,'MISSING_SCORING_GOLD'):self.runone(gold={})
  self.assertFalse(Path(self.args.out).exists())
 def test_invalid_numeric_options_rejected(self):
  for field,value in [('stdout_limit',True),('stderr_limit',1.5),('max_cases',True),('max_cases',.5),('timeout',True)]:
   with self.subTest(field=field,value=value):
    args=copy.deepcopy(self.args);setattr(args,field,value)
    with self.assertRaises(ValueError):run_adapter(args,self.tasks[:1],self.gold,self.catalog)
    self.assertFalse(Path(args.out).exists())
 def test_invalid_track_rejected(self):
  self.args.track='unknown'
  with self.assertRaisesRegex(ValueError,'INVALID_TRACK'):self.runone()
 def test_dependency_change_during_last_case_not_committed(self):
  dep=self.root/'dep';dep.write_text('original');self.args.dependency_file=[str(dep)]
  def changed(*args,**kwargs):
   result=capture(*args,**kwargs);dep.write_text('changed');return result
  with patch('cardiobench.runner.capture',side_effect=changed):
   with self.assertRaisesRegex(ValueError,'DURING_ATTEMPT'):self.runone()
  self.assertEqual(read_json(self.root/'out/checkpoint.json')['state']['records'],[])
  self.assertFalse((self.root/'out/run.lock').exists());dep.write_text('original');self.args.resume=True
  self.assertEqual(self.runone()['overall']['joint_correct'],1)
 def test_adapter_change_during_last_case_not_committed(self):
  def changed(*args,**kwargs):
   result=capture(*args,**kwargs);self.adapter.write_text(self.adapter.read_text()+'\n# changed');return result
  with patch('cardiobench.runner.capture',side_effect=changed):
   with self.assertRaisesRegex(ValueError,'DURING_ATTEMPT'):self.runone()
  self.assertEqual(read_json(self.root/'out/checkpoint.json')['state']['records'],[])
 def test_caller_gold_mutation_does_not_change_snapshot(self):
  gold=copy.deepcopy(self.gold)
  def changed(*args,**kwargs):
   result=capture(*args,**kwargs);gold[self.tasks[0]['id']]['answer']['variable']='WRONG';return result
  with patch('cardiobench.runner.capture',side_effect=changed):self.assertEqual(self.runone(gold=gold)['overall']['joint_correct'],1)
 def test_predictable_temp_symlink_cannot_overwrite_input(self):
  source=self.root/'input';source.write_text('original');(self.root/'report.json.tmp').symlink_to(source)
  dump(self.root/'report.json',{'result':1});self.assertEqual(source.read_text(),'original');self.assertEqual(read_json(self.root/'report.json'),{'result':1})
 def test_cli_dump_failed_replace_preserves_report(self):
  p=self.root/'report.json';p.write_text('{"old":true}')
  with patch('cardiobench.runner.os.replace',side_effect=OSError('write failed')):
   with self.assertRaises(OSError):dump(p,{'new':True})
  self.assertEqual(read_json(p),{'old':True});self.assertEqual(list(self.root.glob('*.tmp')),[])
