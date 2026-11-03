from cardiobench.review import COLUMNS,review_identity
from cardiobench.runner import digest
"""Regression evidence for the 0.4.0 audit fixes and versioned contract changes."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import copy,itertools,json,os,subprocess,sys,unittest,csv
from cardiobench.core import load_release,execute_fixture,summarize,read_json,ROOT,reference
from cardiobench.runner import binding,run_adapter,atomic_json,disclosure,request_payload
from cardiobench.contracts import candidate_contract,REASONS,validate_tasks,validate_disclosure
from cardiobench.io_safety import atomic_bytes

class RoundSixTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.tasks,cls.gold,cls.catalog=load_release()
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.adapter=self.root/'adapter_a.py';self.adapter.write_text('import json,sys\nx=json.load(sys.stdin)\ng='+repr(self.gold)+'\nprint(json.dumps(g[x["task"]["id"]]))',encoding='utf-8')
  self.args=SimpleNamespace(adapter=str(self.adapter),out=str(self.root/'run'),timeout=2.,track='provided-context',resume=False,retry_failed=False,max_cases=None,prompt_file=None,disclosure=None,stdout_limit=10000,stderr_limit=10000,dependency_file=[],dependency_package=[],environment_file=None,adapter_cwd=None)
 def runone(self,tasks=None):return run_adapter(self.args,self.tasks[:1] if tasks is None else tasks,self.gold,self.catalog)
 def local_disclosure(self):return read_json(ROOT/'examples/reference_disclosure.json')
 def test_different_adapter_path_cannot_resume_identical_bytes(self):
  self.runone();other=self.root/'adapter_b.py';other.write_bytes(self.adapter.read_bytes());self.args.adapter=str(other);self.args.resume=True
  with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.runone()
 def test_binding_records_actual_command_and_interpreter(self):
  identity,adapter=binding(self.args,self.tasks[:1],self.catalog,self.gold)
  self.assertEqual(identity['launch_command'],[sys.executable,str(self.adapter.resolve())]);self.assertEqual(identity['python_executable'],sys.executable)
 def test_parser_cannot_overwrite_release_gold(self):
  p=ROOT/'cardiobench/data/gold.json';before=p.read_bytes()
  done=subprocess.run([sys.executable,'-m','cardiobench.sources','--out',str(p)],capture_output=True,text=True,cwd=ROOT)
  self.assertEqual(done.returncode,2);self.assertEqual(p.read_bytes(),before)
 def test_parser_cannot_overwrite_custom_snapshot(self):
  from cardiobench.sources import main
  from cardiobench.io_safety import guard_output
  p=self.root/'source.html';p.write_text('source');q=self.root/'alias.html';q.symlink_to(p)
  with self.assertRaisesRegex(ValueError,'COLLISION'):guard_output(q,[p])
 def test_csv_symlink_target_preserved(self):
  dest=self.root/'results';dest.mkdir();source=self.root/'input.csv';source.write_text('unchanged')
  (dest/'check_results.csv').symlink_to(source)
  done=subprocess.run([sys.executable,'-m','cardiobench','reproduce','--out',str(dest)],capture_output=True,text=True,cwd=ROOT)
  self.assertEqual(done.returncode,0,done.stderr);self.assertEqual(source.read_text(),'unchanged');self.assertFalse((dest/'check_results.csv').is_symlink())
 def test_atomic_bytes_failed_replace_preserves_original(self):
  p=self.root/'report.csv';p.write_text('old')
  with patch('os.replace',side_effect=OSError('injected')):
   with self.assertRaises(OSError):atomic_bytes(p,b'new')
  self.assertEqual(p.read_text(),'old');self.assertFalse(list(self.root.glob('*.tmp')))
 def test_exact_mean_cancellation_all_permutations(self):
  r=copy.deepcopy(next(t['request'] for t in self.tasks if t['id']=='E21'))
  for rows in itertools.permutations(r['left']):
   r['left']=list(rows);self.assertEqual(execute_fixture(r)['weighted_mean'],1/3)
 def test_exact_mean_large_finite_products(self):
  r=next(t['request'] for t in self.tasks if t['id']=='E20');self.assertEqual(execute_fixture(r)['weighted_mean'],1e308)
 def test_tiny_weights_keep_finite_mean(self):
  r=next(t['request'] for t in self.tasks if t['id']=='E24');self.assertEqual(execute_fixture(r)['weighted_mean'],4.0)
 def test_source_clean_gold_remains_identical(self):
  old=read_json(ROOT/'results/v0_3_1/reference_predictions.json')
  self.assertEqual({k:self.gold[k] for k in old},old)
 def test_candidate_reasons_cover_all_scored_reasons(self):
  used={g['reason_code'] for g in self.gold.values() if g['reason_code']};self.assertLessEqual(used,set(REASONS))
 def test_every_task_has_answer_fields_without_gold(self):
  for t in self.tasks:
   c=candidate_contract(t);fields=c['response_schema']['oneOf'][0]['properties']['answer']['required'];self.assertTrue(fields);self.assertNotIn('expected',c);self.assertNotIn('gold',c)
 def test_adapter_contract_matches_export_contract(self):
  self.runone();p=read_json(self.root/'run/requests/S01.json');self.assertEqual(p['response_contract'],candidate_contract(self.tasks[0]))
 def test_closed_book_retains_protocol_but_not_catalog(self):
  self.args.track='closed-book';self.runone();p=read_json(self.root/'run/requests/S01.json');self.assertIn('response_contract',p);self.assertNotIn('catalog',p)
 def test_all_legacy_tasks_have_unchanged_primary_scores(self):
  tasks=self.tasks[:80];preds={t['id']:reference(t,self.catalog) for t in tasks};self.assertEqual(summarize(tasks,self.gold,preds)['overall']['joint_correct'],80)
 def test_w11_alternative_passes_only_secondary_policy(self):
  t=next(t for t in self.tasks if t['id']=='W11');r=copy.deepcopy(self.gold['W11']);r['evidence']=['TRIGLY_J:WTSAF2YR','WEIGHTING:SELECTION'];s=summarize([t],self.gold,{'W11':r})
  self.assertEqual(s['overall']['joint_correct'],0);self.assertEqual(s['policy_adjusted']['overall']['joint_correct'],1)
 def test_w11_irrelevant_evidence_still_fails(self):
  t=next(t for t in self.tasks if t['id']=='W11');r=copy.deepcopy(self.gold['W11']);r['evidence']=['DEMO_J:WTINT2YR','WEIGHTING:SELECTION'];s=summarize([t],self.gold,{'W11':r});self.assertEqual(s['policy_adjusted']['overall']['joint_correct'],0)
 def test_w11_wrong_answer_not_rescued(self):
  t=next(t for t in self.tasks if t['id']=='W11');r=copy.deepcopy(self.gold['W11']);r['answer']['weight']='WTINT2YR';r['evidence']=['TRIGLY_J:WTSAF2YR','WEIGHTING:SELECTION'];s=summarize([t],self.gold,{'W11':r});self.assertEqual(s['policy_adjusted']['overall']['joint_correct'],0)
 def test_duplicate_summary_tasks_rejected(self):
  with self.assertRaisesRegex(ValueError,'DUPLICATE_TASK_ID'):summarize([self.tasks[0]]*2,self.gold,{})
 def test_missing_metadata_rejected_before_creation(self):
  for key in ['canonical_id','group_id','kind','split','cycle','prompt','request']:
   t=copy.deepcopy(self.tasks[:1]);t[0].pop(key)
   with self.subTest(key=key),self.assertRaises(ValueError):self.runone(t)
   self.assertFalse(Path(self.args.out).exists())
 def test_invalid_request_container_rejected(self):
  t=copy.deepcopy(self.tasks[:1]);t[0]['request']=[]
  with self.assertRaisesRegex(ValueError,'REQUEST'):validate_tasks(t,self.gold)
 def test_invalid_subset_rejected(self):
  t=copy.deepcopy(self.tasks[:1]);t[0]['split']='training'
  with self.assertRaisesRegex(ValueError,'SPLIT'):validate_tasks(t,self.gold)
 def test_disclosure_placeholder_rejected(self):
  d=self.local_disclosure();d['notes']={'x':'AUTHOR_TO_COMPLETE'}
  with self.assertRaisesRegex(ValueError,'INCOMPLETE'):validate_disclosure(d,'provided-context')
 def test_disclosure_string_boolean_rejected(self):
  d=self.local_disclosure();d['candidate_gold_access']='false'
  with self.assertRaisesRegex(ValueError,'BOOLEAN'):validate_disclosure(d,'provided-context')
 def test_disclosure_wrong_version_rejected(self):
  d=self.local_disclosure();d['suite_version']='99.0'
  with self.assertRaisesRegex(ValueError,'VERSION'):validate_disclosure(d,'provided-context')
 def test_disclosure_wrong_hash_rejected_before_writes(self):
  d=self.local_disclosure();d['input_task_sha256']='0'*64;p=self.root/'disclosure.json';p.write_text(json.dumps(d));self.args.disclosure=str(p)
  with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):self.runone()
  self.assertFalse(Path(self.args.out).exists())
 def test_external_disclosure_requires_experiment_fields(self):
  d=self.local_disclosure();d['run_kind']='external'
  with self.assertRaisesRegex(ValueError,'INCOMPLETE'):validate_disclosure(d,'provided-context')
 def test_complete_unknown_external_values_are_explicit(self):
  d=self.local_disclosure();d.update(run_kind='external',seed_and_determinism_status='unknown: provider does not expose a seed',tool_call_and_context_budget='one request',hardware_and_operating_system='unknown: remote service',cache_and_warmup_policy='unknown: provider-managed',raw_model_request_and_completion_archive='run/traces',access_date_utc='2026-10-20T00:00:00Z',temperature=None,temperature_unavailable_reason='unknown: not exposed',maximum_output_tokens=None,maximum_output_tokens_unavailable_reason='unknown: not exposed')
  self.assertIs(validate_disclosure(d,'provided-context'),d)
 def test_expansion_covers_each_split_and_family(self):
  for split in ['development','evaluation']:
   for kind in ['leakage','execution']:
    rows=[t for t in self.tasks[80:] if t['split']==split and t['kind']==kind];self.assertEqual(len(rows),6);self.assertEqual(len({t['canonical_id'] for t in rows}),6)
 def test_expansion_groups_do_not_cross(self):
  a={t['group_id'] for t in self.tasks if t['split']=='development'};b={t['group_id'] for t in self.tasks if t['split']=='evaluation'};self.assertFalse(a&b)
 def test_legacy_inventory_content_unchanged(self):
  self.assertEqual([t['id'] for t in self.tasks[:80]],[f'{k}{i:02d}' for k in 'SCWLE' for i in range(1,17)])
 def test_release_counts_match_actual(self):
  from cardiobench.core import DATA
  release=read_json(DATA/'release.json');self.assertEqual(release['checks'],104);self.assertEqual(release['canonical_workloads'],89)
 def test_review_blank_forms_rejected(self):
  from cardiobench.review import read_form
  import importlib.util
  sp=importlib.util.spec_from_file_location('prepare_review',ROOT/'tools/prepare_review.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);m.prepare(self.root/'review')
  with self.assertRaisesRegex(ValueError,'INCOMPLETE_REVIEW'):read_form(self.root/'review/reviewer_A.csv',self.tasks)
 def test_review_duplicate_ids_rejected(self):
  from cardiobench.review import read_form
  p=self.root/'review.csv'
  with p.open('w',newline='') as f:
   w=csv.writer(f);w.writerow(COLUMNS)
   row=['S01',digest(review_identity(self.tasks,self.catalog)),'synthetic-test-only','2026-10-20T00:00:00Z',json.dumps(self.gold['S01']),'test fixture, not human review',''];w.writerow(row);w.writerow(row)
  with self.assertRaisesRegex(ValueError,'TASK_ID'):read_form(p,self.tasks)
 def test_changed_evidence_policy_is_in_binding(self):
  identity,_=binding(self.args,self.tasks[:1],self.catalog,self.gold);self.assertRegex(identity['evidence_policy_sha256'],'^[0-9a-f]{64}$')

