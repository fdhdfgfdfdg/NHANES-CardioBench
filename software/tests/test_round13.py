"""0.4.7 regressions against rehashed invalid bindings, timing and build evidence."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import copy,json,subprocess,sys,unittest
from cardiobench.core import ROOT,load_release,read_json
from cardiobench.runner import digest,file_hash,validate_state,report_documents
from cardiobench.binding_contract import validate_binding
from cardiobench.artifacts import verify_artifacts
from cardiobench.build_environment import preflight_builder,validate_builder,requirements
from cardiobench.process_evidence import validate_process_record

class RoundThirteenTests(unittest.TestCase):
 def setUp(self):
  from test_round8 import RoundEightTests
  RoundEightTests.setUpClass();self.f=RoundEightTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.tasks,self.gold,self.catalog=load_release()
 def bundle(self):return self.f.bundle()
 def binding_mutation(self,change):
  from cardiobench.delivery_evidence import run_summary
  r=self.bundle();states=[]
  for name in ('resume_first_checkpoint.json','resume_run/checkpoint.json'):
   p=r/'validation'/name;e=read_json(p);change(e['state']['binding']);e['sha256']=digest(e['state']);p.write_text(json.dumps(e));states.append(e['state'])
  final=states[-1];selected=[t for t in self.tasks if t['split']=='development']
  for name,value in report_documents(final,selected,self.gold).items():(r/'validation/resume_run'/name).write_text(json.dumps(value))
  p=r/'validation/resume_validation.json';v=read_json(p);v.update(first=run_summary(states[0],len(selected)),resumed=run_summary(final,len(selected)),completed_resume=run_summary(final,len(selected)),checkpoint_sha256=file_hash(r/'validation/resume_run/checkpoint.json'),completed_resume_before_sha256=file_hash(r/'validation/resume_run/checkpoint.json'),first_checkpoint_sha256=file_hash(r/'validation/resume_first_checkpoint.json'));p.write_text(json.dumps(v));self.f.refreeze(r)
  with self.assertRaisesRegex(ValueError,'BINDING'):verify_artifacts(r,True)
 def test_rehashed_negative_timeout_rejected(self):self.binding_mutation(lambda v:v.update(timeout_seconds=-30))
 def test_rehashed_prompt_hash_rejected(self):self.binding_mutation(lambda v:v.update(prompt_sha256='0'*64))
 def test_rehashed_launch_command_rejected(self):self.binding_mutation(lambda v:v.update(launch_command=['unrelated']))
 def test_rehashed_negative_output_limit_rejected(self):self.binding_mutation(lambda v:v.update(stderr_limit_bytes=-1))
 def test_rehashed_boolean_output_limit_rejected(self):self.binding_mutation(lambda v:v.update(stdout_limit_bytes=True))
 def test_rehashed_unknown_binding_field_rejected(self):self.binding_mutation(lambda v:v.update(unchecked_claim=True))
 def test_rehashed_missing_binding_field_rejected(self):self.binding_mutation(lambda v:v.pop('platform'))
 def test_rehashed_environment_injection_rejected(self):self.binding_mutation(lambda v:v['execution']['safe_environment'].update(UNDECLARED='value'))
 def test_rehashed_relative_dependency_path_rejected(self):self.binding_mutation(lambda v:v['execution']['dependency_files_sha256'].update({'relative.py':'0'*64}))
 def test_rehashed_invalid_package_version_type_rejected(self):self.binding_mutation(lambda v:v['execution']['dependency_package_versions'].update(package=1))
 def test_archived_foreign_paths_need_not_exist(self):
  r=self.bundle();v=read_json(r/'validation/resume_run/checkpoint.json')['state']['binding']
  v.update(python_executable='Z:\\old-host\\python.exe',python_executable_resolved='Z:\\old-host\\python.exe',adapter_path='Z:\\old-host\\adapter.py');v['launch_command']=[v['python_executable'],v['adapter_path']];v['execution']['cwd']='Z:\\old-host';v['execution']['dependency_files_sha256']={'Z:\\old-host\\data.json':'0'*64};validate_binding(v)
 def test_live_binding_invalid_limit_rejected(self):
  from types import SimpleNamespace
  from cardiobench.runner import binding
  args=SimpleNamespace(adapter=str(ROOT/'examples/trusted_reference_adapter.py'),prompt_file=None,disclosure=None,track='provided-context',timeout=30,stdout_limit=-1,stderr_limit=64000)
  with self.assertRaisesRegex(ValueError,'OUTPUT_LIMIT'):binding(args,self.tasks,self.catalog,self.gold)
 def test_state_uses_same_binding_validation(self):
  r=self.bundle();e=read_json(r/'validation/resume_run/checkpoint.json');e['state']['binding']['timeout_seconds']=0;e['sha256']=digest(e['state'])
  with self.assertRaisesRegex(ValueError,'BINDING_TIMEOUT'):validate_state(e,e['state']['binding'])
 def process_mutation(self,change):
  r=self.bundle();p=r/'validation/process_timing.json';v=read_json(p);change(v);p.write_text(json.dumps(v));self.f.refreeze(r)
  with self.assertRaisesRegex(ValueError,'PROCESS_'):verify_artifacts(r,True)
 def test_rehashed_impossible_process_seconds_rejected(self):self.process_mutation(lambda v:v.update(seconds=0.000001))
 def test_rehashed_process_command_rejected(self):self.process_mutation(lambda v:v.update(command=['unrelated']))
 def test_rehashed_process_command_output_mismatch(self):self.process_mutation(lambda v:v['command'].__setitem__(-1,'/different/output'))
 def test_rehashed_process_exit_status_rejected(self):self.process_mutation(lambda v:v.update(returncode=1))
 def test_rehashed_process_stdout_mismatch_rejected(self):self.process_mutation(lambda v:v.update(stdout='{}'))
 def test_rehashed_process_unknown_field_rejected(self):self.process_mutation(lambda v:v.update(unchecked_claim=True))
 def test_process_tolerance_boundary(self):
  r=self.bundle();v=read_json(r/'validation/process_timing.json');timing=read_json(r/'validation/process_reproduction/paper_results.json')['timing'];lower=sum(timing['warm_reference_raw_seconds'])+0.3
  v['seconds']=lower-0.0005;validate_process_record(v,timing)
  v['seconds']=lower-0.002
  with self.assertRaisesRegex(ValueError,'ELAPSED'):validate_process_record(v,timing)
 def test_missing_build_backend_fails_before_outputs(self):
  import importlib.metadata
  from tools.check_installation import check
  def missing(name):
   if name=='setuptools':raise importlib.metadata.PackageNotFoundError(name)
   return '1.0'
  out=self.f.root/'installation.json';sdist=self.f.root/'sdist.json'
  with patch('cardiobench.build_environment.importlib.metadata.version',side_effect=missing),patch('tools.check_installation.distribution_verify') as verify:
   with self.assertRaisesRegex(ValueError,'BUILD_ENVIRONMENT_NOT_READY.*setuptools'):check('unused',out,sdist)
  verify.assert_not_called();self.assertFalse(out.exists());self.assertFalse(sdist.exists())
 def test_pinned_build_versions_required(self):
  with patch('cardiobench.build_environment.importlib.metadata.version',return_value='0.0'),patch('cardiobench.build_environment.importlib.util.find_spec',return_value=object()):
   with self.assertRaisesRegex(ValueError,'requires'):preflight_builder(ROOT)
 def test_build_environment_records_versions_and_requirements(self):
  pins,sha=requirements(ROOT)
  with patch('cardiobench.build_environment.importlib.metadata.version',side_effect=lambda n:pins.get(n,'24.0')),patch('cardiobench.build_environment.importlib.util.find_spec',return_value=object()):v=preflight_builder(ROOT)
  self.assertEqual(v['tools'],{'pip':'24.0',**pins});self.assertEqual(v['requirements_sha256'],sha);validate_builder(ROOT,v)
 def test_rehashed_build_environment_version_rejected(self):
  r=self.bundle();p=r/'validation/sdist_build.json';v=read_json(p);v['builder_environment']['tools']['setuptools']='0.0';p.write_text(json.dumps(v));self.f.refreeze(r)
  with self.assertRaisesRegex(ValueError,'BUILD_ENVIRONMENT'):verify_artifacts(r,True)
 def test_rehashed_build_interpreter_mismatch_rejected(self):
  r=self.bundle();p=r/'validation/sdist_build.json';v=read_json(p);v['build_command'][0]='/different/python';p.write_text(json.dumps(v));self.f.refreeze(r)
  with self.assertRaisesRegex(ValueError,'BUILD_INTERPRETER'):verify_artifacts(r,True)
 def test_failed_build_preserves_command_stdout_stderr(self):
  from tools.check_installation import format_command_failure
  error=subprocess.CalledProcessError(1,['python','-m','pip','wheel'],output='build output',stderr='backend missing')
  result=format_command_failure(error)
  for expected in ('pip','wheel','build output','backend missing'):self.assertIn(expected,result)
 def test_ci_bootstraps_pinned_backend_before_offline_check(self):
  text=(ROOT/'.github/workflows/check.yml').read_text();self.assertLess(text.index('pip install -r requirements-build.txt'),text.index('build --no-isolation'));self.assertLess(text.index('build --no-isolation'),text.index('tools/check_installation.py'))
if __name__=='__main__':unittest.main()
