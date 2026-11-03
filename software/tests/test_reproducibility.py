"""Second-round tests for recoverable runs and frozen-source reconstruction."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy, json, tempfile, unittest, time, sys, subprocess, shutil
from cardiobench.core import load_release, ROOT, clean_values, variable
from cardiobench.runner import run_adapter, read_json, atomic_json, capture, digest, validate_state, run_lock
from cardiobench.sources import parse_sources, verify_parsed, parse_component

class ReproducibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tasks,cls.gold,cls.catalog=load_release();cls.tasks=cls.tasks[:2]
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.adapter=self.root/'adapter.py'
        self.adapter.write_text('import json,sys\nfrom pathlib import Path\np=Path(__file__).with_suffix(".count")\nn=int(p.read_text())+1 if p.exists() else 1\np.write_text(str(n))\nx=json.load(sys.stdin)\ng='+repr(self.gold)+'\nprint(json.dumps(g[x["task"]["id"]]))\n')
        self.args=SimpleNamespace(adapter=str(self.adapter),out=str(self.root/'out'),timeout=2.0,track='provided-context',resume=False,retry_failed=False,max_cases=None,prompt_file=None,disclosure=None,stdout_limit=10000,stderr_limit=10000)
    def run_cases(self,tasks=None):return run_adapter(self.args,tasks or self.tasks,self.gold,self.catalog)
    def test_resume_skips_completed_cases(self):
        self.args.max_cases=1;first=self.run_cases();self.assertEqual(first['run']['status'],'partial')
        self.args.resume=True;self.args.max_cases=None;second=self.run_cases()
        self.assertEqual(second['overall']['joint_correct'],2);self.assertEqual(self.adapter.with_suffix('.count').read_text(),'2')
        self.run_cases();self.assertEqual(self.adapter.with_suffix('.count').read_text(),'2')
    def test_fresh_run_cannot_overwrite_existing_results(self):
        self.run_cases()
        with self.assertRaisesRegex(ValueError,'NOT_EMPTY'):self.run_cases()
    def test_resume_changed_adapter_rejected(self):
        self.args.max_cases=1;self.run_cases();self.adapter.write_text(self.adapter.read_text()+'\n# changed\n');self.args.resume=True
        with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.run_cases()
    def test_resume_changed_track_rejected(self):
        self.run_cases();self.args.resume=True;self.args.track='closed-book'
        with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.run_cases()
    def test_resume_changed_timeout_rejected(self):
        self.run_cases();self.args.resume=True;self.args.timeout=3
        with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.run_cases()
    def test_resume_changed_prompt_rejected(self):
        p=self.root/'prompt.txt';p.write_text('original');self.args.prompt_file=str(p);self.run_cases();p.write_text('changed');self.args.resume=True
        with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.run_cases()
    def test_resume_changed_tasks_rejected(self):
        self.run_cases();self.args.resume=True;t=copy.deepcopy(self.tasks);t[0]['prompt']='changed'
        with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.run_cases(t)
    def test_corrupt_checkpoint_rejected(self):
        self.run_cases();p=Path(self.args.out)/'checkpoint.json';v=read_json(p);v['state']['run_id']='corrupt';atomic_json(p,v);self.args.resume=True
        with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):self.run_cases()
    def test_corrupt_request_archive_rejected(self):
        self.run_cases();(Path(self.args.out)/'requests/S01.json').write_text('{}');self.args.resume=True
        with self.assertRaisesRegex(ValueError,'ARCHIVE_MISMATCH'):self.run_cases()
    def test_derived_report_rebuilt_on_resume(self):
        original=self.run_cases();(Path(self.args.out)/'score.json').write_text('broken');self.args.resume=True
        self.assertEqual(self.run_cases(),original)
    def test_failure_terminal_without_retry(self):
        self.adapter.write_text('print("invalid json")');self.run_cases();self.args.resume=True
        report=self.run_cases();self.assertEqual(report['run']['total_attempts'],2);self.assertEqual(report['run']['failed_cases'],2)
    def test_explicit_retry_keeps_attempt_history(self):
        s=self.adapter.read_text().replace('print(json.dumps(g[x["task"]["id"]]))','print("invalid" if n==1 else json.dumps(g[x["task"]["id"]]))');self.adapter.write_text(s)
        self.run_cases(self.tasks[:1]);self.args.resume=True;self.args.retry_failed=True
        result=self.run_cases(self.tasks[:1]);self.assertEqual(result['overall']['joint_correct'],1);self.assertEqual(result['run']['total_attempts'],2)
        state=read_json(Path(self.args.out)/'checkpoint.json')['state'];self.assertEqual(len(state['records'][0]['attempts']),2)
    def test_retry_requires_resume(self):
        self.args.retry_failed=True
        with self.assertRaisesRegex(ValueError,'requires resume'):self.run_cases()
    def test_closed_book_request_omits_catalog(self):
        self.args.track='closed-book';self.run_cases();request=read_json(Path(self.args.out)/'requests/S01.json');self.assertNotIn('catalog',request)
    def test_prompt_archived_and_hashed(self):
        p=self.root/'prompt.txt';p.write_text('Return JSON only.');self.args.prompt_file=str(p);self.run_cases()
        request=read_json(Path(self.args.out)/'requests/S01.json');manifest=read_json(Path(self.args.out)/'run_manifest.json')
        self.assertEqual(request['prompt'],'Return JSON only.');self.assertEqual(manifest['binding']['prompt_sha256'],digest(request['prompt']))
    def test_incomplete_disclosure_rejected(self):
        p=self.root/'disclosure.json';p.write_text('{}');self.args.disclosure=str(p)
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_DISCLOSURE'):self.run_cases()
    def test_mismatched_disclosure_track_rejected(self):
        p=self.root/'disclosure.json';v={k:'declared' for k in ['system_name_and_exact_version','provider_or_checkpoint','source_access_policy','retry_policy','token_use_and_cost_or_unavailable_reason']};v['condition']='closed_book';p.write_text(json.dumps(v));self.args.disclosure=str(p)
        with self.assertRaisesRegex(ValueError,'TRACK_MISMATCH'):self.run_cases()
    def test_output_limit_is_applied_during_capture(self):
        self.adapter.write_text('import os\nwhile True: os.write(1,b"x"*4096)\n')
        start=time.monotonic();r=capture(self.adapter,b'{}',2,8192,8192)
        self.assertEqual(r['error'],'ADAPTER_OUTPUT_LIMIT');self.assertLessEqual(len(r['stdout']),8192);self.assertLess(time.monotonic()-start,2)
    def test_stderr_limit(self):
        self.adapter.write_text('import os\nwhile True: os.write(2,b"e"*4096)\n');r=capture(self.adapter,b'{}',2,8192,8192)
        self.assertEqual(r['error'],'ADAPTER_OUTPUT_LIMIT');self.assertLessEqual(len(r['stderr']),8192)
    def test_timeout_keeps_partial_output(self):
        self.adapter.write_text('import sys,time\nprint("started",flush=True)\ntime.sleep(10)\n');r=capture(self.adapter,b'{}',0.2,8192,8192)
        self.assertEqual(r['error'],'ADAPTER_TIMEOUT');self.assertIn('started',r['stdout'])
    def test_run_lock_rejects_concurrent_writer(self):
        dest=Path(self.args.out);dest.mkdir()
        with run_lock(dest):
            with self.assertRaisesRegex(ValueError,'RUN_LOCK_EXISTS'):self.run_cases()
    def test_sources_reconstruct_all_metadata(self):
        result=verify_parsed();self.assertEqual(result['variable_occurrences'],383);self.assertEqual(result['components'],12)
    def test_snapshot_tamper_rejected_before_parse(self):
        root=self.root/'copy';shutil.copytree(ROOT/'sources',root/'sources');p=root/'sources/snapshots/MCQ_J.html';p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'SOURCE_HASH_MISMATCH'):parse_sources(root)
    def test_parser_preserves_original_anchor_and_check_item(self):
        p=parse_sources();self.assertTrue(p['MCQ_J']['MCQ160F']['url'].endswith('#MCQ160f'));self.assertEqual(p['MCQ_J']['MCQ515']['question'],'')
    def test_duplicate_variable_rejected(self):
        section='<div class="pagebreak"><h3 id="X">X</h3><dl><dt>Variable Name:</dt><dd>X</dd></dl></div>'
        with self.assertRaisesRegex(ValueError,'DUPLICATE_VARIABLE'):parse_component(section*2,'TEST','https://example.invalid')
    def test_literal_dot_missing_code(self):
        self.assertEqual(clean_values(variable(self.catalog,'MCQ_J','MCQ160F'),['.',7.0,1]),[None,None,1])
