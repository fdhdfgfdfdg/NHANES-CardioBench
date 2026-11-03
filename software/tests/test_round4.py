"""Evidence consistency, protected outputs, declared environment and fault recovery."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import base64,copy,hashlib,json,os,signal,subprocess,sys,tempfile,threading,time,unittest
from cardiobench.core import ROOT,load_release,read_json,reference,grade,lexical_context
from cardiobench.runner import run_adapter,validate_state,digest,atomic_json,capture,binding
from cardiobench.io_safety import guard_output

class RoundFourTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.tasks,cls.gold,cls.catalog=load_release()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.adapter=self.root/'adapter.py'
  self.adapter.write_text('import json,sys\nx=json.load(sys.stdin)\ng='+repr(self.gold)+'\nprint(json.dumps(g[x["task"]["id"]]))')
  self.args=SimpleNamespace(adapter=str(self.adapter),out=str(self.root/'out'),timeout=2.,track='provided-context',resume=False,retry_failed=False,max_cases=None,prompt_file=None,disclosure=None,stdout_limit=10000,stderr_limit=10000,dependency_file=[],environment_file=None,adapter_cwd=None)
 def runone(self,gold=None):return run_adapter(self.args,self.tasks[:1],self.gold if gold is None else gold,self.catalog)
 def state(self):self.runone();return read_json(self.root/'out/checkpoint.json')['state']
 def rejects(self,change):
  s=self.state();change(s['records'][0]['attempts'][0]);
  with self.assertRaises(ValueError):validate_state({'state':s,'sha256':digest(s)},s['binding'])
 def test_stdout_mismatch(self):self.rejects(lambda a:a.update(stdout='not JSON'))
 def test_returncode_mismatch(self):self.rejects(lambda a:a.update(returncode=9))
 def test_stream_hash_mismatch(self):self.rejects(lambda a:a.update(stdout_sha256='0'*64))
 def test_stream_count_mismatch(self):self.rejects(lambda a:a.update(stdout_retained_bytes=0))
 def test_stream_bytes_mismatch(self):self.rejects(lambda a:a.update(stdout_base64='%%%'))
 def test_response_mismatch(self):self.rejects(lambda a:a['response']['answer'].update(variable='WRONG'))
 def test_timestamp_outside_run(self):self.rejects(lambda a:a.update(started_utc='1900-01-01T00:00:00+00:00'))
 def test_missing_capture_fields(self):self.rejects(lambda a:a.pop('stdout_base64'))
 def test_scoring_gold_change_rejected(self):
  self.runone();g=copy.deepcopy(self.gold);g[self.tasks[0]['id']]['answer']['variable']='WRONG';self.args.resume=True
  with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.runone(g)
 def test_response_output_alias(self):
  p=self.root/'input.json';p.write_text('{}')
  with self.assertRaisesRegex(ValueError,'COLLISION'):guard_output(p,[p])
  self.assertEqual(p.read_text(),'{}')
 def test_response_symlink_alias(self):
  p=self.root/'input';p.write_text('{}');q=self.root/'link';q.symlink_to(p)
  with self.assertRaisesRegex(ValueError,'COLLISION'):guard_output(q,[p])
 def test_response_hardlink_alias(self):
  p=self.root/'input';p.write_text('{}');q=self.root/'link';os.link(p,q)
  with self.assertRaisesRegex(ValueError,'COLLISION'):guard_output(q,[p])
 def test_release_protected(self):
  with self.assertRaisesRegex(ValueError,'PROTECTED'):guard_output(ROOT/'cardiobench/data/gold.json')
 def test_frozen_results_protected(self):
  with self.assertRaisesRegex(ValueError,'PROTECTED'):guard_output(ROOT/'results/paper/new.json')
 def test_adapter_cwd_default(self):
  self.adapter.write_text('import json\nfrom pathlib import Path\nprint(Path("response.json").read_text())');(self.root/'response.json').write_text(json.dumps(self.gold[self.tasks[0]['id']]))
  self.assertEqual(self.runone()['overall']['joint_correct'],1)
 def test_dependency_change_rejected(self):
  p=self.root/'dep';p.write_text('one');self.args.dependency_file=[str(p)];self.runone();p.write_text('two');self.args.resume=True
  with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.runone()
 def test_cwd_change_rejected(self):
  self.runone();q=self.root/'other';q.mkdir();self.args.adapter_cwd=str(q);self.args.resume=True
  with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.runone()
 def test_safe_environment_change_rejected(self):
  p=self.root/'env.json';p.write_text('{"OMP_NUM_THREADS":"1"}');self.args.environment_file=str(p);self.runone();p.write_text('{"OMP_NUM_THREADS":"2"}');self.args.resume=True
  with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.runone()
 def test_secret_config_refused(self):
  p=self.root/'env.json';p.write_text('{"API_KEY":"do-not-record"}');self.args.environment_file=str(p)
  with self.assertRaisesRegex(ValueError,'INVALID_ENVIRONMENT'):self.runone()
  self.assertFalse(Path(self.args.out).exists())
 def test_launch_failure_checkpoint_resumes(self):
  with patch('cardiobench.runner.capture',side_effect=OSError('launch failed')):r=self.runone()
  self.assertEqual(r['run']['failed_cases'],1);self.args.resume=True;self.args.retry_failed=True
  self.assertEqual(self.runone()['overall']['joint_correct'],1)
 def test_failed_atomic_replace_preserves_previous(self):
  p=self.root/'state.json';atomic_json(p,{'old':True});before=p.read_bytes()
  with patch('cardiobench.runner.os.replace',side_effect=OSError('disk failure')):
   with self.assertRaises(OSError):atomic_json(p,{'new':True})
  self.assertEqual(p.read_bytes(),before);self.assertEqual(list(self.root.glob('*.tmp')),[])
 def test_report_failure_recovers_committed_case(self):
  from cardiobench.runner import reports
  count=[0]
  def fail_second(*args):
   count[0]+=1
   if count[0]==2:raise OSError('report write failed')
   return reports(*args)
  with patch('cardiobench.runner.reports',side_effect=fail_second):
   with self.assertRaises(OSError):self.runone()
  self.assertFalse((self.root/'out/run.lock').exists());self.args.resume=True
  self.assertEqual(self.runone()['run']['total_attempts'],1)
 @unittest.skipUnless(os.name=='posix','POSIX process groups')
 def test_descendant_holding_pipe_times_out(self):
  self.adapter.write_text('import subprocess,sys\nsubprocess.Popen([sys.executable,"-c","import time;time.sleep(10)"])')
  start=time.monotonic();r=capture(self.adapter,b'{}',.2,1000,1000)
  self.assertEqual(r['error'],'ADAPTER_TIMEOUT');self.assertLess(time.monotonic()-start,2)
 @unittest.skipUnless(os.name=='posix','POSIX signal interruption')
 def test_keyboard_interrupt_cleans_capture(self):
  self.adapter.write_text('import time\ntime.sleep(10)')
  timer=threading.Timer(.2,lambda:os.kill(os.getpid(),signal.SIGINT));timer.start()
  try:
   with self.assertRaises(KeyboardInterrupt):capture(self.adapter,b'{}',5,1000,1000)
  finally:timer.join()
 def test_development_tutorials_match_declared_answers(self):
  rows=read_json(ROOT/'examples/development_examples.json')['examples'];ids={t['id'] for t in self.tasks}
  self.assertEqual(len(rows),4)
  for t in rows:self.assertNotIn(t['id'],ids);self.assertTrue(grade(reference(t,self.catalog),t['expected'],t)['joint_correct'])
 def test_context_baseline_ignores_gold(self):
  t=next(t for t in self.tasks if t['kind']=='semantic');a=lexical_context(t,self.catalog)
  self.assertEqual(a,lexical_context(t,self.catalog));self.assertIn(a['answer']['variable'],{v['variable'] for v in self.catalog['variables']})
 def test_review_materials_start_pending(self):
  import importlib.util,csv
  spec=importlib.util.spec_from_file_location('review',ROOT/'tools/prepare_review.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  out=self.root/'review';r=mod.prepare(out);self.assertEqual(r['reviewers_completed'],0)
  with (out/'adjudication.csv').open() as stream:rows=list(csv.DictReader(stream))
  self.assertEqual(len(rows),104);self.assertTrue(all(row['status']=='pending' for row in rows))
  self.assertNotIn('gold',read_json(out/'reviewer_inputs.json'))
  with self.assertRaisesRegex(ValueError,'EXISTS'):mod.prepare(out)

 def test_declared_package_version_change_rejected(self):
  self.args.dependency_package=['example-package']
  with patch('cardiobench.runner.importlib.metadata.version',return_value='1.0'):self.runone()
  self.args.resume=True
  with patch('cardiobench.runner.importlib.metadata.version',return_value='2.0'):
   with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.runone()

 @unittest.skipUnless(os.name=='posix','POSIX hard kill')
 def test_hard_kill_resumes_committed_case(self):
  marker=self.root/'blocked'
  self.adapter.write_text('import json,sys,time,os\nfrom pathlib import Path\nx=json.load(sys.stdin)\ng='+repr(self.gold)+'\np=Path('+repr(str(marker))+')\nif x["task"]["id"]=='+repr(self.tasks[1]['id'])+' and not p.exists():\n p.write_text(str(os.getpid()))\n time.sleep(20)\nprint(json.dumps(g[x["task"]["id"]]))')
  script='from types import SimpleNamespace;from cardiobench.core import load_release;from cardiobench.runner import run_adapter;t,g,c=load_release();run_adapter(SimpleNamespace(**'+repr(vars(self.args))+'),t[:2],g,c)'
  proc=subprocess.Popen([sys.executable,'-c',script],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  try:
   deadline=time.monotonic()+5
   while not marker.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.01)
   self.assertTrue(marker.exists());proc.kill();proc.wait(timeout=2)
   os.killpg(int(marker.read_text()),signal.SIGKILL)
   state=read_json(self.root/'out/checkpoint.json')['state'];self.assertEqual(len(state['records']),1)
   self.assertTrue((self.root/'out/run.lock').exists());(self.root/'out/run.lock').unlink()
   self.args.resume=True;r=run_adapter(self.args,self.tasks[:2],self.gold,self.catalog)
   self.assertEqual(r['run']['total_attempts'],2);self.assertEqual(r['overall']['joint_correct'],2)
  finally:
   if proc.poll() is None:proc.kill();proc.wait()
   proc.stderr.close()
