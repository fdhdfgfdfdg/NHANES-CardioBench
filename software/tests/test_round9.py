"""Five v0.4.3 corrections; synthetic validation records only."""
from pathlib import Path
import copy,csv,io,json,shutil,tarfile,unittest,zipfile
from cardiobench import __version__
from cardiobench.core import ROOT,load_release,read_json,summarize,distribution_verify
from cardiobench.artifacts import verify_artifacts,freeze_artifacts,_archive,extract_package
from cardiobench.runner import digest

class RoundNineTests(unittest.TestCase):
 def setUp(self):
  from test_round8 import RoundEightTests
  RoundEightTests.setUpClass()
  self.fixture=RoundEightTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
  self.root=self.fixture.root;self.tasks,self.gold,self.catalog=load_release()
 def bundle(self):return self.fixture.bundle()
 def reject_change(self,name,change,pattern):
  root=self.bundle();p=root/name;value=read_json(p);change(value);p.write_text(json.dumps(value));self.fixture.refreeze(root)
  with self.assertRaisesRegex(ValueError,pattern):verify_artifacts(root,True)
 def test_old_resume_version_rejected_after_refreeze(self):
  self.reject_change('validation/resume_validation.json',lambda v:v.update(version='0.4.2',status='failed'),'RESUME_EVIDENCE')
 def test_resume_core_binding_rejected(self):
  self.reject_change('validation/resume_validation.json',lambda v:v['evidence_binding'].update(core_manifest_sha256='0'*64),'RESUME_EVIDENCE')
 def test_resume_claimed_counts_checked(self):
  self.reject_change('validation/resume_validation.json',lambda v:v.update(final_joint_correct=0),'RESUME_RESULT')
 def test_resume_unchanged_digest_checked(self):
  self.reject_change('validation/resume_validation.json',lambda v:v.update(completed_resume_before_sha256='0'*64),'RESUME_RESULT')
 def test_rehashed_checkpoint_wrong_binding_rejected(self):
  def mutate(v):v['state']['binding']['tasks_sha256']='0'*64;v['sha256']=digest(v['state'])
  self.reject_change('validation/resume_run/checkpoint.json',mutate,'CHECKPOINT_BINDING')
 def test_missing_resume_request_rejected(self):
  root=self.bundle();next((root/'validation/resume_run/requests').iterdir()).unlink();self.fixture.refreeze(root)
  with self.assertRaises((ValueError,OSError)):verify_artifacts(root,True)
 def test_old_timing_version_rejected(self):
  self.reject_change('validation/process_timing.json',lambda v:v.update(version='0.4.2'),'PROCESS_EVIDENCE')
 def test_negative_timing_rejected(self):
  self.reject_change('validation/process_timing.json',lambda v:v.update(seconds=-1),'PROCESS_SECONDS')
 def test_bool_timing_rejected(self):
  self.reject_change('validation/process_timing.json',lambda v:v.update(seconds=True),'PROCESS_SECONDS')
 def test_process_summary_rescored(self):
  self.reject_change('validation/process_timing.json',lambda v:v['result']['reference'].update(joint_correct=0),'PROCESS_(SUMMARY|STDOUT)')
 def test_process_raw_result_binding_checked(self):
  self.reject_change('validation/process_reproduction/paper_results.json',lambda v:v.update(version='0.4.2'),'PROCESS_RESULT_BINDING')
 def test_malformed_expected_answers_rejected(self):
  root=self.bundle();(root/'review_materials/expected_answers_after_review.json').write_text('NOT JSON');self.fixture.refreeze(root)
  with self.assertRaises(ValueError):verify_artifacts(root,True)
 def test_changed_expected_answer_rejected(self):
  self.reject_change('review_materials/expected_answers_after_review.json',lambda v:v['W11']['answer'].update(weight='WRONG'),'EXPECTED_ANSWERS')
 def test_adjudication_task_range_checked(self):
  root=self.bundle();p=root/'review_materials/adjudication.csv';p.write_text(p.read_text().replace('S01,pending','UNKNOWN,pending'));self.fixture.refreeze(root)
  with self.assertRaisesRegex(ValueError,'ADJUDICATION'):verify_artifacts(root,True)
 def test_adjudication_completed_claim_rejected(self):
  root=self.bundle();p=root/'review_materials/adjudication.csv';p.write_text(p.read_text().replace('S01,pending','S01,completed'));self.fixture.refreeze(root)
  with self.assertRaisesRegex(ValueError,'ADJUDICATION'):verify_artifacts(root,True)
 def test_nonblank_reviewer_form_not_preparation(self):
  root=self.bundle();p=root/'review_materials/reviewer_A.csv'
  with p.open(newline='') as f:reader=csv.DictReader(f);rows=list(reader);columns=reader.fieldnames
  rows[0]['reviewer_id']='synthetic-A'
  with p.open('w',newline='') as f:w=csv.DictWriter(f,columns);w.writeheader();w.writerows(rows)
  self.fixture.refreeze(root)
  with self.assertRaisesRegex(ValueError,'REVIEW_MATERIAL'):verify_artifacts(root,True)
 def test_changed_preparation_instructions_rejected(self):
  root=self.bundle();(root/'review_materials/README.txt').write_text('Reviews completed');self.fixture.refreeze(root)
  with self.assertRaisesRegex(ValueError,'INSTRUCTIONS'):verify_artifacts(root,True)
 def test_stale_staging_gate_binding_rejected(self):
  self.reject_change('validation/release_gate.json',lambda v:v['evidence_binding'].update(version='0.4.2'),'RELEASE_GATE')
 def archive(self,members,kind='tar'):
  p=self.root/('paths.whl' if kind=='zip' else 'paths.tar.gz')
  if kind=='zip':
   with zipfile.ZipFile(p,'w') as f:
    for name,data in members:f.writestr(name,data)
  else:
   with tarfile.open(p,'w:gz') as f:
    for name,data in members:info=tarfile.TarInfo(name);info.size=len(data);f.addfile(info,io.BytesIO(data))
  return p
 def test_cross_platform_roots_rejected_before_extract(self):
  for name in ['C:/PKG-INFO','C:PKG-INFO','/absolute','//server/share','a/../b','a/./b','a//b','a\\b','a/NUL.txt','a/end.','a/end ','a/COM1.txt']:
   with self.subTest(name=name),self.assertRaisesRegex(ValueError,'MEMBER_INVALID'):_archive(self.archive([(name,b'x')]))
 def test_zip_drive_paths_also_rejected(self):
  with self.assertRaisesRegex(ValueError,'MEMBER_INVALID'):_archive(self.archive([('C:/core.py',b'x')],'zip'))
 def test_case_fold_collision_rejected(self):
  with self.assertRaisesRegex(ValueError,'COLLISION'):_archive(self.archive([('a/README',b'a'),('a/readme',b'b')]))
 def test_file_directory_collision_both_orders(self):
  for members in [[('a',b'x'),('a/b',b'y')],[('a/b',b'y'),('a',b'x')]]:
   with self.assertRaisesRegex(ValueError,'COLLISION'):_archive(self.archive(members))
 def test_bad_member_leaves_no_partial_extraction(self):
  dest=self.root/'extract';dest.mkdir();p=self.archive([('okay/file',b'ok'),('C:/bad',b'bad')])
  with self.assertRaisesRegex(ValueError,'MEMBER_INVALID'):extract_package(p,dest)
  self.assertEqual(list(dest.iterdir()),[])
 def test_resolved_extraction_containment(self):
  dest=self.root/'extract';dest.mkdir();outside=self.root/'outside';outside.mkdir()
  try:(dest/'linked').symlink_to(outside,target_is_directory=True)
  except OSError:self.skipTest('symlinks unavailable')
  with self.assertRaisesRegex(ValueError,'EXTRACTION_ESCAPE'):extract_package(self.archive([('linked/file',b'bad')]),dest)
  self.assertFalse((outside/'file').exists())
 def test_normal_archive_extracts(self):
  dest=self.root/'extract';dest.mkdir();extract_package(self.archive([('source/core.py',b'valid')]),dest)
  self.assertEqual((dest/'source/core.py').read_bytes(),b'valid')
 def adjusted(self,gold):
  task=next(t for t in self.tasks if t['id']=='W11');pred=copy.deepcopy(gold);pred['evidence']=['TRIGLY_J:WTSAF2YR','WEIGHTING:SELECTION']
  return summarize([task],{'W11':gold},{'W11':pred})
 def test_custom_gold_answer_loses_alternative(self):
  gold=copy.deepcopy(self.gold['W11']);gold['answer']['weight']='WTMEC2YR';gold['evidence']=['DEMO_J:WTMEC2YR','WEIGHTING:SELECTION'];r=self.adjusted(gold)
  self.assertFalse(r['policy_adjusted']['rows'][0]['alternative_policy_applicable']);self.assertEqual(r['policy_adjusted']['overall']['joint_correct'],0)
 def test_custom_gold_evidence_loses_alternative(self):
  gold=copy.deepcopy(self.gold['W11']);gold['evidence']=['CORPUS:MANIFEST'];self.assertFalse(self.adjusted(gold)['policy_adjusted']['rows'][0]['alternative_policy_applicable'])
 def test_custom_gold_status_loses_alternative(self):
  gold={'status':'abstain','answer':{},'evidence':['CORPUS:MANIFEST'],'reason_code':'NOT_IN_RELEASE'};self.assertFalse(self.adjusted(gold)['policy_adjusted']['rows'][0]['alternative_policy_applicable'])
 def test_equivalent_gold_order_keeps_alternative(self):
  gold=dict(reversed(list(self.gold['W11'].items())));r=self.adjusted(gold)
  self.assertEqual(r['overall']['joint_correct'],0);self.assertEqual(r['policy_adjusted']['overall']['joint_correct'],1)
 def core_copy(self):
  root=self.root/'source';root.mkdir();manifest=read_json(ROOT/'MANIFEST_SHA256.json')
  for name in [*manifest['files'],'MANIFEST_SHA256.json']:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
  return root
 def test_explicit_root_valid_source_passes(self):
  root=self.core_copy();self.assertEqual(distribution_verify(root),len(read_json(root/'MANIFEST_SHA256.json')['files']))
 def test_damaged_target_core_refuses_freeze(self):
  root=self.core_copy();(root/'README.md').write_text('wrong target')
  with self.assertRaisesRegex(ValueError,'DISTRIBUTION_HASH_MISMATCH: README'):freeze_artifacts(root)
  self.assertFalse((root/'ARTIFACTS_SHA256.json').exists())
 def test_explicit_installed_resource_root_passes(self):
  source=self.core_copy();package=self.root/'installed/cardiobench';package.mkdir(parents=True);release=package/'_release';release.mkdir()
  manifest=read_json(source/'MANIFEST_SHA256.json')
  for name in [*manifest['files'],'MANIFEST_SHA256.json']:
   dest=(package.parent/name) if name.startswith('cardiobench/') else release/name
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,dest)
  self.assertEqual(distribution_verify(release),len(manifest['files']))
  (package/'core.py').write_text('bad')
  with self.assertRaisesRegex(ValueError,'DISTRIBUTION_HASH'):distribution_verify(release)
 def doc_checker(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('release_gate_test',ROOT/'tools/check_release.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module.validate_current_docs
 def test_current_docs_checked(self):self.doc_checker()(ROOT)
 def test_stale_current_protocol_rejected(self):
  root=self.core_copy();p=root/'docs/protocol.md';p.write_text(p.read_text().replace('# Protocol '+__version__,'# Protocol 0.4.2',1))
  with self.assertRaisesRegex(ValueError,'CURRENT_DOCUMENT_VERSION'):self.doc_checker()(root)
 def test_missing_historical_audit_link_rejected(self):
  root=self.core_copy();p=root/'README.md';p.write_text(p.read_text().replace('docs/audit_resolution_v0_4_2.md','docs/audit_resolution.md'))
  with self.assertRaisesRegex(ValueError,'HISTORICAL_AUDIT_LINK'):self.doc_checker()(root)
