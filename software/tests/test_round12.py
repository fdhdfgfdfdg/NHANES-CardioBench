"""0.4.6 audit regressions; altered evidence is synthetic test data only."""
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import base64,copy,hashlib,json,os,shutil,subprocess,sys,unittest
from cardiobench import __version__
from cardiobench.core import ROOT,load_release,read_json,parse_json,INTEGER_LIMIT,ensure_finite
from cardiobench.runner import canonical,digest,file_hash,validate_state,run_adapter
from cardiobench.artifacts import verify_artifacts,validate_package
from cardiobench.verification_evidence import validate_verification,core_observations,NOT_BUNDLED

class RoundTwelveTests(unittest.TestCase):
 def setUp(self):
  from test_round8 import RoundEightTests
  RoundEightTests.setUpClass();self.f=RoundEightTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.tasks,self.gold,self.catalog=load_release()
 def bundle(self):return self.f.bundle()
 def paper_mutation(self,change):
  r=self.bundle();p=r/'validation/process_reproduction/paper_results.json';v=read_json(p);change(v);p.write_text(json.dumps(v))
  q=r/'validation/process_timing.json';v=read_json(q);v['paper_results_sha256']=file_hash(p);q.write_text(json.dumps(v));self.f.refreeze(r)
  with self.assertRaisesRegex(ValueError,'VERIFICATION'):verify_artifacts(r,True)
 def test_installed_resource_layout_observations(self):
  r=self.bundle();package=self.f.root/'installed/cardiobench';resource=package/'_release';resource.mkdir(parents=True)
  shutil.copytree(r/'cardiobench/data',package/'data');shutil.copytree(r/'sources',resource/'sources');shutil.copy2(r/'MANIFEST_SHA256.json',resource/'MANIFEST_SHA256.json')
  self.assertEqual(core_observations(resource),core_observations(r))
 def test_verification_count_corruption(self):self.paper_mutation(lambda p:p['verification'].update(checks=0))
 def test_verification_false_group_claim(self):self.paper_mutation(lambda p:p['verification'].update(groups_disjoint=False))
 def test_verification_parsed_metadata_corruption(self):self.paper_mutation(lambda p:p['verification']['parsed_metadata_verified'].update(variable_occurrences=999))
 def test_verification_boolean_count(self):self.paper_mutation(lambda p:p['verification'].update(source_snapshots_verified=True))
 def test_verification_unknown_field(self):self.paper_mutation(lambda p:p['verification'].update(unchecked_claim=True))
 def test_verification_snapshot_digest_mismatch(self):
  self.paper_mutation(lambda p:p['verification'].update(core_manifest_snapshot=p['verification']['core_manifest_snapshot']+' '))
 def test_primary_snapshot_allows_only_report_changes(self):
  r=self.bundle();m=read_json(r/'MANIFEST_SHA256.json');name='results/paper/paper_results.json';m['files'][name]='0'*64
  (r/'MANIFEST_SHA256.json').write_text(json.dumps(m));v={**core_observations(r),'artifact_verification':dict(NOT_BUNDLED)}
  m['files'][name]='1'*64;(r/'MANIFEST_SHA256.json').write_text(json.dumps(m))
  validate_verification(r,v,allow_primary_staging=True)
  with self.assertRaisesRegex(ValueError,'VERIFICATION'):validate_verification(r,v)
 def test_primary_snapshot_cannot_hide_changed_code(self):
  r=self.bundle();v={**core_observations(r),'artifact_verification':dict(NOT_BUNDLED)};m=read_json(r/'MANIFEST_SHA256.json')
  m['files']['cardiobench/core.py']='0'*64;(r/'MANIFEST_SHA256.json').write_text(json.dumps(m))
  with self.assertRaisesRegex(ValueError,'VERIFICATION'):validate_verification(r,v,allow_primary_staging=True)
 def test_primary_snapshot_requires_staging_artifact_scope(self):
  r=self.bundle();v={**core_observations(r),'artifact_verification':{'status':'verified'}}
  with self.assertRaisesRegex(ValueError,'VERIFICATION'):validate_verification(r,v,allow_primary_staging=True)
 def gate_mutation(self,change):
  r=self.bundle();p=r/'validation/release_gate.json';v=read_json(p);change(v);p.write_text(json.dumps(v));self.f.refreeze(r)
  with self.assertRaisesRegex(ValueError,'RELEASE_GATE'):verify_artifacts(r,True)
 def test_staging_gate_test_count_recomputed(self):self.gate_mutation(lambda v:v.update(test_methods=v['test_methods']+1))
 def test_staging_gate_distribution_count_recomputed(self):self.gate_mutation(lambda v:v.update(distribution_files_verified=0))
 def test_staging_gate_unknown_field_rejected(self):self.gate_mutation(lambda v:v.update(unchecked_claim=True))
 def sdist_change(self,change,error):
  r=self.bundle();prefix='nhanes_cardiobench-'+__version__+'/'
  p=self.f.package(r,'sdist',changed=lambda m:change(m,prefix))
  with self.assertRaisesRegex(ValueError,error):validate_package(p,r)
 def test_sdist_extra_python_rejected(self):self.sdist_change(lambda m,p:m.update({p+'cardiobench/unreviewed.py':b'PAYLOAD=True\n'}),'UNEXPECTED_MEMBER')
 def test_sdist_extra_data_rejected(self):self.sdist_change(lambda m,p:m.update({p+'cardiobench/data/extra.json':b'{}'}),'UNEXPECTED_MEMBER')
 def test_sdist_extra_build_configuration_rejected(self):self.sdist_change(lambda m,p:m.update({p+'setup.cfg':b'[egg_info]\ntag_build=\ntag_date=0\n[aliases]\ninstall=other\n'}),'CONFIGURATION')
 def test_sdist_wrong_entry_point_rejected(self):self.sdist_change(lambda m,p:m.update({p+'nhanes_cardiobench.egg-info/entry_points.txt':b'[console_scripts]\ncardiobench=unexpected:main\n'}),'CONFIGURATION')
 def test_sdist_external_dependency_link_rejected(self):self.sdist_change(lambda m,p:m.update({p+'nhanes_cardiobench.egg-info/dependency_links.txt':b'https://invalid.example/package\n'}),'METADATA')
 def test_sdist_sources_missing_core_rejected(self):self.sdist_change(lambda m,p:m.update({p+'nhanes_cardiobench.egg-info/SOURCES.txt':b'MANIFEST_SHA256.json\n'}),'SOURCES')
 def test_sdist_generated_setup_configuration_allowed(self):
  r=self.bundle();p=self.f.package(r,'sdist',changed=lambda m:m.update({'nhanes_cardiobench-'+__version__+'/setup.cfg':b'[egg_info]\ntag_build = \ntag_date = 0\n\n'}));validate_package(p,r)
 def timeout_envelope(self,seconds):
  r=self.f.root/'bundle'
  if not r.exists():r=self.bundle()
  e=read_json(r/'validation/resume_run/checkpoint.json');a=e['state']['records'][0]['attempts'][0]
  a.update(error='ADAPTER_TIMEOUT',response=None,seconds=seconds);e['sha256']=digest(e['state']);return e
 def test_zero_duration_timeout_rejected(self):
  e=self.timeout_envelope(0)
  with self.assertRaisesRegex(ValueError,'TIMEOUT_DURATION'):validate_state(e,e['state']['binding'])
 def test_short_duration_timeout_rejected(self):
  e=self.timeout_envelope(29.5)
  with self.assertRaisesRegex(ValueError,'TIMEOUT_DURATION'):validate_state(e,e['state']['binding'])
 def test_timeout_rounding_tolerance_and_elapsed_allowed(self):
  for seconds in (29.9995,30.0,30.5):
   with self.subTest(seconds=seconds):
    e=self.timeout_envelope(seconds);validate_state(e,e['state']['binding'])
 def test_actual_timeout_resume_and_retry(self):
  adapter=self.f.root/'slow.py';adapter.write_text('import time\ntime.sleep(1)\n')
  out=self.f.root/'run';args=SimpleNamespace(adapter=str(adapter),prompt_file=None,disclosure=None,track='provided-context',timeout=0.05,stdout_limit=10000,stderr_limit=1000,max_cases=1,out=str(out),resume=False,retry_failed=False)
  selected=[self.tasks[0]];first=run_adapter(args,selected,self.gold,self.catalog);self.assertEqual(first['run']['failed_cases'],1)
  original=(out/'checkpoint.json').read_bytes();e=read_json(out/'checkpoint.json');self.assertEqual(e['state']['records'][0]['attempts'][0]['error'],'ADAPTER_TIMEOUT')
  e['state']['records'][0]['attempts'][0]['seconds']=0;e['sha256']=digest(e['state']);(out/'checkpoint.json').write_bytes(canonical(e));score_before=(out/'score.json').read_bytes();args.resume=True
  with self.assertRaisesRegex(ValueError,'TIMEOUT_DURATION'):run_adapter(args,selected,self.gold,self.catalog)
  self.assertEqual(score_before,(out/'score.json').read_bytes());(out/'checkpoint.json').write_bytes(original)
  result=run_adapter(args,selected,self.gold,self.catalog);self.assertEqual(result['run']['total_attempts'],1);self.assertEqual(original,(out/'checkpoint.json').read_bytes())
  args.retry_failed=True;result=run_adapter(args,selected,self.gold,self.catalog);self.assertEqual(result['run']['total_attempts'],2)
 def with_limit(self,limit,fn):
  if not hasattr(sys,'set_int_max_str_digits'):self.skipTest('Interpreter has no configurable integer string limit')
  previous=sys.get_int_max_str_digits();sys.set_int_max_str_digits(limit)
  try:return fn()
  finally:sys.set_int_max_str_digits(previous)
 def test_low_integer_limit_reported_as_environment(self):
  def check():
   for n in (10,640,641,1000,4096):
    with self.subTest(digits=n),self.assertRaisesRegex(ValueError,'INCOMPATIBLE_INTEGER_ENVIRONMENT'):parse_json('9'*n)
  self.with_limit(640,check)
 def test_low_integer_limit_blocks_serializer(self):
  self.with_limit(640,lambda:self.assertRaisesRegex(ValueError,'INCOMPATIBLE_INTEGER_ENVIRONMENT',canonical,{'n':10**1000}))
 def test_supported_integer_settings_keep_boundary(self):
  def check():
   for sign in ('','-'):
    n=parse_json(sign+'9'*4096);self.assertEqual(abs(n),INTEGER_LIMIT-1);self.assertEqual(canonical(n).decode(),sign+'9'*4096)
    with self.assertRaisesRegex(ValueError,'INTEGER_LIMIT_EXCEEDED'):parse_json(sign+'9'*4097)
  for limit in (0,4096,4300):self.with_limit(limit,check)
 def test_integer_setting_not_modified_by_library(self):
  if not hasattr(sys,'get_int_max_str_digits'):self.skipTest('No interpreter setting')
  before=sys.get_int_max_str_digits();parse_json('123');canonical({'x':1});self.assertEqual(sys.get_int_max_str_digits(),before)
 def test_incompatible_cli_environment_no_output(self):
  if not hasattr(sys,'get_int_max_str_digits'):self.skipTest('No configurable interpreter setting')
  out=self.f.root/'export.json';env=os.environ.copy();env['PYTHONINTMAXSTRDIGITS']='640'
  done=subprocess.run([sys.executable,'-m','cardiobench','export','--out',str(out)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
  self.assertEqual(done.returncode,2);self.assertIn('INCOMPATIBLE_INTEGER_ENVIRONMENT',done.stderr);self.assertNotIn('Traceback',done.stderr);self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
