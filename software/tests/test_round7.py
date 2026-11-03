"""Regression probes for the nine v0.4.1 audit findings; synthetic tests, not human review."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import copy,csv,json,hashlib,subprocess,sys,unittest,io
from contextlib import redirect_stdout
from cardiobench.core import load_release,grade,reference,parse_json,read_json,trace_dependencies,validate_response,summarize,ROOT,DATA
from cardiobench.contracts import validate_tasks,validate_task_response,candidate_contract
from cardiobench.runner import run_adapter,canonical
from cardiobench.artifacts import inventory,sha,verify_artifacts,PROFILE
from cardiobench import __version__
from cardiobench.review import COLUMNS,review_identity
from cardiobench.runner import digest

class RoundSevenTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.tasks,cls.gold,cls.catalog=load_release()
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.adapter=self.root/'adapter.py'
  self.args=SimpleNamespace(adapter=str(self.adapter),out=str(self.root/'run'),timeout=3.,track='provided-context',resume=False,retry_failed=False,max_cases=None,prompt_file=None,disclosure=None,stdout_limit=10000,stderr_limit=10000,dependency_file=[],dependency_package=[],environment_file=None,adapter_cwd=None)
 def task(self,tid):return copy.deepcopy(next(t for t in self.tasks if t['id']==tid))
 def run_cases(self,tasks=None):return run_adapter(self.args,self.tasks[:1] if tasks is None else tasks,self.gold,self.catalog)
 def adapter_response(self,r):self.adapter.write_text('print('+repr(json.dumps(r))+')',encoding='utf-8')
 def form(self,name,reviewer,changes=None):
  p=self.root/name
  with p.open('w',newline='',encoding='utf-8') as f:
   w=csv.writer(f);w.writerow(COLUMNS)
   for t in self.tasks:
    response=copy.deepcopy(self.gold[t['id']])
    if changes:changes(response)
    w.writerow([t['id'],digest(review_identity(self.tasks,self.catalog)),reviewer,'2026-10-20T00:00:00Z',json.dumps(response),'synthetic test rationale','synthetic concern'])
  return p
 def test_overdeep_json_rejected_before_decoder_recursion(self):
  for n in [129,988,994,1500]:
   with self.subTest(depth=n),self.assertRaisesRegex(ValueError,'DEPTH'):parse_json('['*n+'0'+']'*n)
 def test_brackets_and_escaped_quotes_in_string_not_depth(self):
  v='['*500+'"\\]';self.assertEqual(parse_json(json.dumps(v)),v)
 def test_maximum_json_depth_round_trip(self):
  raw='['*128+'0'+']'*128;self.assertEqual(parse_json(canonical(parse_json(raw)).decode()),parse_json(raw))
 def test_response_depth_limit(self):
  r=copy.deepcopy(self.gold['S01']);v=0
  for _ in range(33):v=[v]
  r['answer']={'x':v}
  with self.assertRaisesRegex(ValueError,'DEPTH'):validate_response(r)
 def test_deep_failure_checkpoint_resumes_remaining_case(self):
  self.adapter.write_text('import json,sys\nx=json.load(sys.stdin)\nif x["task"]["id"]=="S01":print("["*988+"0"+"]"*988)\nelse:print('+repr(json.dumps(self.gold['S02']))+')')
  self.args.max_cases=1;first=self.run_cases(self.tasks[:2]);self.assertEqual(first['run']['format_failed_cases'],1)
  self.assertIsNone(read_json(self.root/'run/checkpoint.json')['state']['records'][0]['attempts'][0]['response'])
  self.args.resume=True;self.args.max_cases=None;last=self.run_cases(self.tasks[:2]);self.assertEqual(last['run']['completed_cases'],2);self.assertEqual(last['overall']['joint_correct'],1)
 def test_negative_execution_count_is_format_error(self):
  t=self.task('E01');r=copy.deepcopy(self.gold['E01']);r['answer']['cohort_n']=-1;self.assertFalse(grade(r,self.gold['E01'],t)['schema_valid'])
 def test_integer_token_constraint_is_explicit_and_enforced(self):
  t=self.task('E01');r=copy.deepcopy(self.gold['E01']);r['answer']['cohort_n']=1.0
  self.assertFalse(grade(r,self.gold['E01'],t)['schema_valid']);self.assertTrue(candidate_contract(t)['response_schema']['oneOf'][0]['properties']['answer']['properties']['cohort_n']['x-integer-token-only'])
 def test_unknown_reason_rejected(self):
  r={'status':'reject','answer':{},'evidence':[],'reason_code':'WRONG_REASON'}
  with self.assertRaisesRegex(ValueError,'UNKNOWN_REASON'):validate_task_response(self.tasks[0],r)
 def test_clean_strings_reference_self_grade(self):
  t=next(copy.deepcopy(x) for x in self.tasks if x['kind']=='coding' and x['request']['operation']=='clean' and x['request']['variable']=='RIDAGEYR');t['request']['values']=['7','9','77','80',None]
  r=reference(t,self.catalog);self.assertEqual(r['answer']['values'],t['request']['values']);self.assertTrue(grade(r,r,t)['joint_correct'])
 def test_conversion_strings_rejected(self):
  t=next(x for x in self.tasks if x['kind']=='coding' and x['request']['operation']=='convert_glucose');r=reference(t,self.catalog);r['answer']['values']=['1']
  with self.assertRaises(ValueError):validate_task_response(t,r)
 def test_all_perturbations_now_schema_valid(self):
  from cardiobench.__main__ import mutations
  result=mutations(self.tasks,self.gold);self.assertEqual(result['schema_valid_records'],312);self.assertEqual(result['detected'],312)
 def test_invented_review_answer_rejected(self):
  from cardiobench.review import read_form
  def mutate(r):r.update(status='answer',answer={'invented':True},reason_code=None)
  with self.assertRaisesRegex(ValueError,'ANSWER_FIELDS'):read_form(self.form('a.csv','synthetic-A',mutate),self.tasks)
 def test_review_wrong_but_well_shaped_answers_retained(self):
  from cardiobench.review import read_form
  def mutate(r):
   if 'variable' in r['answer']:r['answer']['variable']='WRONG_BUT_WELL_SHAPED'
  rows,_=read_form(self.form('a.csv','synthetic-A',mutate),self.tasks);self.assertEqual(rows['S01']['response']['answer']['variable'],'WRONG_BUT_WELL_SHAPED')
 def test_review_provenance_and_rationale_preserved(self):
  from cardiobench.review import compare
  a=self.form('a.csv','synthetic-A');b=self.form('b.csv','synthetic-B');report=compare(a,b,self.root/'comparison.json')
  self.assertEqual(report['provenance']['form_A_sha256'],sha(a));self.assertEqual(report['rows'][0]['review_A']['evidence_rationale'],'synthetic test rationale');self.assertEqual(report['rows'][0]['review_B']['policy_concern'],'synthetic concern');self.assertEqual(report['rows'][0]['review_A']['reviewed_utc'],'2026-10-20T00:00:00Z');self.assertEqual(report['rows'][0]['adjudication_status'],'pending')
 def test_review_duplicate_columns_rejected(self):
  from cardiobench.review import read_form
  p=self.form('a.csv','synthetic-A');raw=p.read_text();p.write_text(raw.replace('policy_concern','policy_concern,policy_concern',1))
  with self.assertRaisesRegex(ValueError,'COLUMNS'):read_form(p,self.tasks)
 def test_review_extra_cell_rejected(self):
  from cardiobench.review import read_form
  p=self.form('a.csv','synthetic-A');lines=p.read_text().splitlines();lines[1]+=',extra';p.write_text('\n'.join(lines))
  with self.assertRaisesRegex(ValueError,'WIDTH'):read_form(p,self.tasks)
 def test_shape_failure_is_retryable_and_history_retained(self):
  r=copy.deepcopy(self.gold['S01']);r['answer']={};self.adapter_response(r);first=self.run_cases();self.assertEqual(first['run']['format_failed_cases'],1);self.assertEqual(first['run']['execution_failed_cases'],0)
  self.args.resume=True;self.args.retry_failed=True;last=self.run_cases();self.assertEqual(last['run']['total_attempts'],2);self.assertEqual(last['run']['failed_cases'],1)
 def test_incorrect_valid_answer_not_retryable(self):
  r=copy.deepcopy(self.gold['S01']);r['answer']['variable']='WRONG';self.adapter_response(r);first=self.run_cases();self.assertEqual(first['run']['incorrect_answer_cases'],1);self.assertEqual(first['run']['failed_cases'],0)
  self.args.resume=True;self.args.retry_failed=True;self.assertEqual(self.run_cases()['run']['total_attempts'],1)
 def test_execution_failure_separate_from_format_failure(self):
  self.adapter.write_text('raise SystemExit(7)');report=self.run_cases();self.assertEqual(report['run']['execution_failed_cases'],1);self.assertEqual(report['run']['format_failed_cases'],0)
 def test_empty_semantic_request_rejected_before_output(self):
  self.adapter_response(self.gold['S01']);t=self.task('S01');t['request']={}
  with self.assertRaisesRegex(ValueError,'REQUEST'):self.run_cases([t])
  self.assertFalse(Path(self.args.out).exists())
 def test_empty_gold_and_prediction_do_not_pass(self):
  t=self.task('S01');r=copy.deepcopy(self.gold['S01']);r['answer']={}
  with self.assertRaisesRegex(ValueError,'ANSWER_FIELDS'):summarize([t],{'S01':r},{'S01':r})
 def test_family_request_fields_typed(self):
  for tid,request in [('C01',{'operation':'unit'}),('W01',{'files':[],'analysis_cycle':'2017-2018'}),('L01',{'label_sources':[],'feature_dependencies':{'x':[1]}})]:
   t=self.task(tid);t['request']=request
   with self.subTest(tid=tid),self.assertRaises(ValueError):validate_tasks([t],self.gold)
 def test_malformed_execution_reject_fixtures_remain_valid(self):
  cases=[t for t in self.tasks if t['kind']=='execution' and self.gold[t['id']]['status']=='reject'];self.assertTrue(cases);self.assertEqual(validate_tasks(cases,self.gold),cases)
 def test_resource_generation_uses_binary_writes(self):
  # Simulate a platform text writer that would translate newlines: no resource uses it.
  import runpy,shutil
  root=self.root/'regen';(root/'tools').mkdir(parents=True);(root/'sources').mkdir();(root/'cardiobench/data').mkdir(parents=True)
  for name in ['curate_workloads.py','extension_workloads.py']:shutil.copy2(ROOT/'tools'/name,root/'tools'/name)
  shutil.copy2(ROOT/'sources/parsed_codebooks.json',root/'sources/parsed_codebooks.json')
  with redirect_stdout(io.StringIO()),patch.object(Path,'write_text',side_effect=AssertionError('platform-dependent text write')),patch.object(sys,'path',[str(root/'tools'),*sys.path]):runpy.run_path(str(root/'tools/curate_workloads.py'))
  for name in ['tasks.json','gold.json','catalog.json','positive_control_routes.json','release.json','evidence_policy.json']:self.assertEqual((root/'cardiobench/data'/name).read_bytes(),(DATA/name).read_bytes())
 def freeze(self):
  (self.root/'MANIFEST_SHA256.json').write_text('{}');(self.root/'packages').mkdir();(self.root/'packages/example.whl').write_bytes(b'fixture');(self.root/'validation').mkdir();(self.root/'validation/test.json').write_text('{}')
  (self.root/'ARTIFACTS_SHA256.json').write_text(json.dumps({'version':__version__,'profile':PROFILE,'algorithm':'sha256','core_manifest_sha256':sha(self.root/'MANIFEST_SHA256.json'),'files':inventory(self.root)}))
 def test_modified_wheel_detected(self):
  self.freeze();(self.root/'packages/example.whl').write_bytes(b'modified')
  with self.assertRaisesRegex(ValueError,'ARTIFACT_HASH'):verify_artifacts(self.root,True)
 def test_modified_validation_detected(self):
  self.freeze();(self.root/'validation/test.json').write_text('{"modified":true}')
  with self.assertRaisesRegex(ValueError,'ARTIFACT_HASH'):verify_artifacts(self.root,True)
 def test_added_artifact_detected(self):
  self.freeze();(self.root/'validation/added.txt').write_text('added')
  with self.assertRaisesRegex(ValueError,'ARTIFACT_HASH'):verify_artifacts(self.root,True)
 def test_missing_outer_manifest_not_silently_accepted(self):
  self.freeze();(self.root/'ARTIFACTS_SHA256.json').unlink()
  with self.assertRaisesRegex(ValueError,'MANIFEST_MISSING'):verify_artifacts(self.root)
 def test_installed_core_scope_explicit(self):
  self.assertEqual(verify_artifacts(self.root)['status'],'not bundled')
  with self.assertRaisesRegex(ValueError,'MANIFEST_MISSING'):verify_artifacts(self.root,True)
 def test_runtime_cannot_write_frozen_artifact_trees(self):
  from cardiobench.io_safety import guard_output
  for name in ['validation/new.json','packages/new.whl','review_materials/new.csv','ARTIFACTS_SHA256.json']:
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'PROTECTED'):guard_output(ROOT/name)
 def test_secondary_success_diagnostic_consistent(self):
  t=self.task('W11');r=copy.deepcopy(self.gold['W11']);r['evidence']=['TRIGLY_J:WTSAF2YR','WEIGHTING:SELECTION'];s=summarize([t],self.gold,{'W11':r});row=s['policy_adjusted']['rows'][0]
  self.assertTrue(row['joint_correct']);self.assertIsNone(row['error']);self.assertEqual(row['primary_error'],'EVIDENCE_MISMATCH')
 def test_long_valid_dependency_chain(self):
  graph={'f0':['label']};graph.update({f'f{i}':[f'f{i-1}'] for i in range(1,1201)});self.assertEqual(len(trace_dependencies(['label'],graph)),1201)
 def test_disconnected_cycle_rejected_iteratively(self):
  with self.assertRaisesRegex(ValueError,'CYCLIC'):trace_dependencies(['label'],{'valid':['label'],'a':['b'],'b':['a']})
 def test_graph_node_limit_explicit(self):
  with self.assertRaisesRegex(ValueError,'GRAPH_LIMIT'):trace_dependencies([],{f'n{i}':[] for i in range(10001)})
 def test_graph_edge_limit_explicit(self):
  graph={f'n{i}':[f'x{j}' for j in range(101)] for i in range(1000)}
  with self.assertRaisesRegex(ValueError,'GRAPH_LIMIT'):trace_dependencies([],graph)
 def test_diamond_and_unrelated_branch(self):
  self.assertEqual(trace_dependencies(['label'],{'a':['label'],'b':['a'],'c':['a'],'d':['b','c'],'u':['raw']}),['a','b','c','d'])
