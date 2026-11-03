"""Regression coverage for scoring, input encoding and checkpoint validation."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from cardiobench.core import load_release,grade,parse_json,summarize,ROOT
from cardiobench.runner import run_adapter,read_json,atomic_json,digest,validate_state,capture

class RoundThreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tasks,cls.gold,cls.catalog=load_release()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.adapter=self.root/'adapter.py';self.adapter.write_text('import json,sys\nx=json.load(sys.stdin)\ng='+repr(self.gold)+'\nprint(json.dumps(g[x["task"]["id"]]))\n')
        self.args=SimpleNamespace(adapter=str(self.adapter),out=str(self.root/'out'),timeout=2.0,track='provided-context',resume=False,retry_failed=False,max_cases=None,prompt_file=None,disclosure=None,stdout_limit=10000,stderr_limit=10000)
    def run_one(self):return run_adapter(self.args,self.tasks[:1],self.gold,self.catalog)
    def state(self):
        self.run_one();return read_json(self.root/'out/checkpoint.json')['state']
    def reject(self,mutate):
        s=self.state();mutate(s)
        with self.assertRaises(ValueError):validate_state({'state':s,'sha256':digest(s)},s.get('binding'))
    def test_huge_integer_float_comparison_is_failure(self):
        e=next(v for v in self.gold.values() if any(type(x) is float for x in v['answer'].values()));a=copy.deepcopy(e)
        for k,v in a['answer'].items():
            if type(v) is float:a['answer'][k]=10**400
        self.assertFalse(grade(a,e,{'kind':'execution','request':{}})['joint_correct'])
    def test_empty_summary_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'EMPTY_TASK_SELECTION'):summarize([],{}, {})
    def test_empty_run_leaves_no_output_directory(self):
        with self.assertRaisesRegex(ValueError,'EMPTY_TASK_SELECTION'):run_adapter(self.args,[],self.gold,self.catalog)
        self.assertFalse(Path(self.args.out).exists())
    def test_checkpoint_required_fields(self):self.reject(lambda s:s.pop('run_id'))
    def test_checkpoint_record_container(self):self.reject(lambda s:s.update(records={}))
    def test_checkpoint_record_type(self):self.reject(lambda s:s['records'].append(None))
    def test_checkpoint_negative_duration(self):self.reject(lambda s:s['records'][0]['attempts'][0].update(seconds=-1))
    def test_checkpoint_boolean_duration(self):self.reject(lambda s:s['records'][0]['attempts'][0].update(seconds=True))
    def test_checkpoint_invalid_error_type(self):self.reject(lambda s:s['records'][0]['attempts'][0].update(error=[]))
    def test_checkpoint_missing_stdout(self):self.reject(lambda s:s['records'][0]['attempts'][0].pop('stdout'))
    def test_checkpoint_naive_timestamp(self):self.reject(lambda s:s.update(created_utc='2026-10-14T00:00:00'))
    def test_success_cannot_have_later_attempt(self):self.reject(lambda s:s['records'][0]['attempts'].append(copy.deepcopy(s['records'][0]['attempts'][0])))
    def test_request_and_record_changed_together_rejected(self):
        s=self.state();request=self.root/'out/requests/S01.json';atomic_json(request,{})
        s['records'][0]['attempts'][0]['request_sha256']=digest({});atomic_json(self.root/'out/checkpoint.json',{'state':s,'sha256':digest(s)})
        self.args.resume=True
        with self.assertRaisesRegex(ValueError,'ARCHIVE_MISMATCH'):self.run_one()
    def test_earlier_attempt_request_is_checked(self):
        self.adapter.write_text('print("invalid")');self.run_one();self.args.resume=True;self.args.retry_failed=True;self.run_one()
        p=self.root/'out/checkpoint.json';s=read_json(p)['state'];s['records'][0]['attempts'][0]['request_sha256']='0'*64;atomic_json(p,{'state':s,'sha256':digest(s)})
        with self.assertRaisesRegex(ValueError,'ARCHIVE_MISMATCH'):self.run_one()
    def test_invalid_utf8_stdout_is_failed(self):
        self.adapter.write_text('import os\nos.write(1,b\'{"status":"abstain","answer":{},"evidence":[],"reason_code":"\\xff"}\')')
        r=self.run_one();self.assertEqual(r['run']['error_counts'],{'ADAPTER_INVALID_UTF8':1})
    def test_unpaired_surrogate_json_is_rejected(self):
        with self.assertRaises(ValueError):parse_json('{"x":"\\ud800"}')
    def test_surrogate_adapter_output_does_not_abort_run(self):
        self.adapter.write_text('print(\'{"status":"abstain","answer":{},"evidence":[],"reason_code":"\\\\ud800"}\')')
        r=run_adapter(self.args,self.tasks[:2],self.gold,self.catalog);self.assertEqual(r['run']['completed_cases'],2);self.assertEqual(r['run']['failed_cases'],2)
    def test_raw_output_digest(self):
        self.adapter.write_text('import os\nos.write(1,b"abc")');r=capture(self.adapter,b'{}',2,1000,1000)
        self.assertEqual(r['stdout_sha256'],__import__('hashlib').sha256(b'abc').hexdigest());self.assertEqual(r['stdout_retained_bytes'],3)
    def test_execution_development_selection_is_now_present(self):
        out=self.root/'score.json';responses=self.root/'responses.json';responses.write_text('{}')
        p=subprocess.run([sys.executable,'-m','cardiobench','score','--split','development','--kind','execution','--responses',str(responses),'--out',str(out)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(read_json(out)['overall']['checks'],6)
    def test_deep_json_cli_has_controlled_error(self):
        out=self.root/'score.json';responses=self.root/'responses.json';responses.write_text('['*2000+'0'+']'*2000)
        p=subprocess.run([sys.executable,'-m','cardiobench','score','--responses',str(responses),'--out',str(out)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertNotIn('Traceback',p.stderr);self.assertFalse(out.exists())
    def test_cli_rejects_changed_release_before_adapter_runs(self):
        import shutil
        target=self.root/'release';shutil.copytree(ROOT,target,ignore=shutil.ignore_patterns('__pycache__','build','*.egg-info'))
        p=target/'cardiobench/data/gold.json';p.write_bytes(p.read_bytes()+b' ')
        marker=self.root/'ran';self.adapter.write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()')
        result=subprocess.run([sys.executable,'-m','cardiobench','run-adapter','--adapter',str(self.adapter),'--out',self.args.out],cwd=target,capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertIn('DISTRIBUTION_HASH_MISMATCH',result.stderr);self.assertFalse(marker.exists());self.assertFalse(Path(self.args.out).exists())
