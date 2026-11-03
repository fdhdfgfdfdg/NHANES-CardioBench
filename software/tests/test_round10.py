"""Regressions for six 0.4.4 fixes; synthetic records are not release evidence."""
from pathlib import Path
import copy,json,subprocess,sys,tarfile,io,math,unittest,zipfile
from cardiobench import __version__
from cardiobench.core import ROOT,load_release,read_json,reference,convert_glucose_values
from cardiobench.contracts import validate_tasks
from cardiobench.artifacts import verify_artifacts,validate_package,member_name,_archive,validate_release_hygiene

class RoundTenTests(unittest.TestCase):
 def setUp(self):
  from test_round8 import RoundEightTests
  RoundEightTests.setUpClass();self.fixture=RoundEightTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
  self.root=self.fixture.root
 def bundle(self):return self.fixture.bundle()
 def mutate(self,name,change,error):
  root=self.bundle();path=root/name;value=read_json(path);change(value);path.write_text(json.dumps(value));self.fixture.refreeze(root)
  with self.assertRaisesRegex(ValueError,error):verify_artifacts(root,True)
 def test_derived_predictions_cannot_be_empty(self):
  self.mutate('validation/resume_run/predictions.json',lambda v:v.clear(),'DERIVED_REPORT')
 def test_derived_score_cannot_disagree(self):
  self.mutate('validation/resume_run/score.json',lambda v:v['overall'].update(joint_correct=0),'DERIVED_REPORT')
 def test_derived_trace_must_match_capture(self):
  self.mutate('validation/resume_run/traces.json',lambda v:v[0].update(stdout='changed'),'DERIVED_REPORT')
 def test_derived_manifest_must_match_binding(self):
  self.mutate('validation/resume_run/run_manifest.json',lambda v:v['binding'].update(track='closed-book'),'DERIVED_REPORT')
 def test_required_derived_report_missing(self):
  root=self.bundle();(root/'validation/resume_run/score.json').unlink();self.fixture.refreeze(root)
  with self.assertRaisesRegex(ValueError,'REQUIRED_DELIVERY'):verify_artifacts(root,True)
 def test_installation_empty_checks_rejected(self):
  self.mutate('validation/installation.json',lambda v:v.update(checks=[]),'CHECKS_INCOMPLETE')
 def test_installation_missing_console_check_rejected(self):
  self.mutate('validation/installation.json',lambda v:v['checks'].pop(),'CHECKS_INCOMPLETE')
 def test_installation_failed_command_rejected(self):
  self.mutate('validation/installation.json',lambda v:v['checks'][0].update(returncode=1),'COMMAND_FAILED')
 def test_installation_boolean_exit_code_rejected(self):
  self.mutate('validation/installation.json',lambda v:v['checks'][0].update(returncode=False),'COMMAND_FAILED')
 def test_installation_wrong_verification_contents(self):
  self.mutate('validation/installation.json',lambda v:v['checks'][0].update(stdout='{}'),'VERIFY_RESULT')
 def test_installation_wrong_reproduction_contents(self):
  self.mutate('validation/installation.json',lambda v:v['checks'][1].update(stdout='{}'),'REPRODUCTION')
 def test_installation_wrong_source_parse(self):
  self.mutate('validation/installation.json',lambda v:v['checks'][2].update(stdout='{}'),'SOURCE_RESULT')
 def test_installation_wrong_console_command(self):
  self.mutate('validation/installation.json',lambda v:v['checks'][4]['command'].__setitem__(0,'wrong-executable'),'COMMAND_MISMATCH')
 def test_installation_empty_console_help(self):
  self.mutate('validation/installation.json',lambda v:v['checks'][3].update(stdout=''),'CONSOLE_HELP')
 def test_missing_rebuilt_wheel_rejected(self):
  self.mutate('validation/sdist_build.json',lambda v:v.pop('rebuilt_wheel'),'REBUILD_BINDING')
 def test_rebuilt_wheel_wrong_core_rejected(self):
  self.mutate('validation/sdist_build.json',lambda v:v['rebuilt_wheel'].update(core_manifest_sha256='0'*64),'REBUILD_BINDING')
 def test_missing_build_result_rejected(self):
  self.mutate('validation/sdist_build.json',lambda v:v.pop('build_returncode'),'BUILD_RESULT')
 def test_network_build_command_rejected(self):
  self.mutate('validation/sdist_build.json',lambda v:v['build_command'].remove('--no-index'),'BUILD_COMMAND')
 def test_process_scope_must_match_verification(self):
  self.mutate('validation/process_timing.json',lambda v:v.update(verification_scope='verified'),'VERIFICATION_SCOPE')
 def test_wrong_entry_point_rejected(self):
  root=self.bundle();path=self.fixture.package(root,'wheel',changed=lambda m:m.update({'nhanes_cardiobench-'+__version__+'.dist-info/entry_points.txt':b'[console_scripts]\ncardiobench = cardiobench.__main__:missing\n'}))
  with self.assertRaisesRegex(ValueError,'ENTRY_POINT'):validate_package(path,root)
 def test_missing_wheel_metadata_rejected(self):
  root=self.bundle();path=self.fixture.package(root,'wheel',changed=lambda m:m.pop('nhanes_cardiobench-'+__version__+'.dist-info/WHEEL'))
  with self.assertRaisesRegex(ValueError,'METADATA_MISSING'):validate_package(path,root)
 def test_extra_wheel_payload_rejected(self):
  root=self.bundle();path=self.fixture.package(root,'wheel',changed=lambda m:m.update({'extra.py':b'pass'}))
  with self.assertRaisesRegex(ValueError,'UNEXPECTED_MEMBER'):validate_package(path,root)
 def test_wrong_record_digest_rejected(self):
  root=self.bundle();path=root/('packages/nhanes_cardiobench-'+__version__+'-py3-none-any.whl')
  with zipfile.ZipFile(path) as z:members={n:z.read(n) for n in z.namelist()}
  name='nhanes_cardiobench-'+__version__+'.dist-info/entry_points.txt';members[name]+=b'\n'
  with zipfile.ZipFile(path,'w') as z:
   for name,data in members.items():z.writestr(name,data)
  with self.assertRaisesRegex(ValueError,'RECORD_HASH'):validate_package(path,root)
 def test_superscript_device_names_rejected(self):
  for name in ('COM¹.txt','COM²','COM³.json','LPT¹.txt','LPT²','LPT³.bin','sub/COM¹.txt','conin$','CONOUT$.txt'):
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'MEMBER_INVALID'):member_name(name)
 def test_nondevice_unicode_names_allowed(self):
  for name in ('report¹.txt','COM10.txt','company.txt','sub/normal.json'):self.assertEqual(member_name(name),name)
 def test_device_names_rejected_in_archive(self):
  path=self.root/'bad.tar.gz'
  with tarfile.open(path,'w:gz') as f:
   info=tarfile.TarInfo('source/COM¹.txt');info.size=1;f.addfile(info,io.BytesIO(b'x'))
  with self.assertRaisesRegex(ValueError,'MEMBER_INVALID'):_archive(path)
 def test_large_integer_glucose_finite_result(self):
  tasks,gold,catalog=load_release();t=next(copy.deepcopy(t) for t in tasks if t['kind']=='coding' and t['request']['operation']=='convert_glucose');t['request']['values']=[10**309]
  validate_tasks([t],gold);result=reference(t,catalog)
  self.assertEqual(result['status'],'answer');self.assertTrue(math.isfinite(result['answer']['values'][0]));self.assertEqual(result['answer']['values'][0],5.551e307)
 def test_glucose_overflow_is_structured_rejection(self):
  tasks,gold,catalog=load_release();t=next(copy.deepcopy(t) for t in tasks if t['kind']=='coding' and t['request']['operation']=='convert_glucose');t['request']['values']=[10**400]
  validate_tasks([t],gold);result=reference(t,catalog)
  self.assertEqual(result['status'],'reject');self.assertEqual(result['reason_code'],'NONFINITE_RESULT')
 def test_glucose_exact_decimal_rounding(self):
  self.assertEqual(convert_glucose_values([1,3,-1,-3],0.0005,3),[0.0,0.002,0.0,-0.002])
 def test_glucose_bool_and_nonfinite_rejected(self):
  for value in [True,float('inf'),float('nan'),'1']:
   with self.subTest(value=value),self.assertRaises(ValueError):convert_glucose_values([value],0.05551,3)
 def test_released_conversion_answers_unchanged(self):
  tasks,gold,catalog=load_release()
  for task in tasks:
   if task['kind']=='coding' and task['request']['operation']=='convert_glucose':self.assertEqual(reference(task,catalog),gold[task['id']])
 def test_current_lock_blocks_delivery(self):
  root=self.bundle();(root/'validation/resume_run/run.lock').write_text('stale');self.fixture.refreeze(root)
  with self.assertRaisesRegex(ValueError,'TRANSIENT_DELIVERY_FILE'):verify_artifacts(root,True)
 def test_current_temp_blocks_delivery(self):
  root=self.bundle();(root/'validation/partial.tmp').write_text('incomplete');self.fixture.refreeze(root)
  with self.assertRaisesRegex(ValueError,'TRANSIENT_DELIVERY_FILE'):verify_artifacts(root,True)
 def test_historical_locks_remain_archived(self):
  root=self.bundle();archive=root/'validation/v0_4_3/resume_run';archive.mkdir(parents=True);(archive/'run.lock').write_text('historical observation');validate_release_hygiene(root)
 def test_runtime_relative_output_from_another_directory(self):
  done=subprocess.run([sys.executable,str(ROOT/'tools/check_runtime.py'),'--out','relative-runtime'],cwd=self.root,text=True,capture_output=True,timeout=120)
  self.assertEqual(done.returncode,0,done.stderr);out=self.root/'relative-runtime';report=read_json(out/'resume_validation.json')
  self.assertEqual(report['final_joint_correct'],32);self.assertTrue(report['completed_checkpoint_unchanged']);self.assertFalse((out/'resume_run/run.lock').exists())
  timing=read_json(out/'process_timing.json');paper=read_json(out/'process_reproduction/paper_results.json')
  self.assertEqual(timing['verification_scope'],paper['verification']['artifact_verification']['status'])
  self.assertEqual(Path(timing['result']['out']),out/'process_reproduction')

if __name__=='__main__':unittest.main()
