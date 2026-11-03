"""Six v0.4.2 audit regressions. Review records are synthetic test fixtures only."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest,copy,json,csv,io,zipfile,tarfile,hashlib,subprocess,sys,shutil
from cardiobench import __version__
from cardiobench.core import load_release,grade,summarize,reference,execute_fixture,ROOT,DATA,read_json
from cardiobench.contracts import validate_tasks,candidate_contract,CONTRACT_VERSION
from cardiobench.review import review_identity,COLUMNS,compare,read_form,MAX_FIELD_CHARS,MAX_FILE_BYTES,MAX_RESPONSE_BYTES
from cardiobench.runner import digest
from cardiobench.artifacts import PROFILE,REQUIRED_FILES,sha,inventory,validate_package,validate_packages,validate_delivery,verify_artifacts

class RoundEightTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.tasks,cls.gold,cls.catalog=load_release()
 def setUp(self):self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def task(self,tid):return copy.deepcopy(next(t for t in self.tasks if t['id']==tid))
 def form(self,name='a.csv',reviewer='synthetic-A',change=None):
  rows=[];binding=digest(review_identity(self.tasks,self.catalog))
  for t in self.tasks:rows.append(dict(zip(COLUMNS,[t['id'],binding,reviewer,'2026-10-21T00:00:00Z',json.dumps(self.gold[t['id']]),'synthetic rationale, not human review',''])))
  if change:change(rows)
  path=self.root/name
  with path.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(rows)
  return path
 def test_review_committed_identity_recorded(self):
  result=compare(self.form(),self.form('b.csv','synthetic-B'),self.root/'out.json')
  self.assertEqual(result['provenance']['review_input_identity'],review_identity(self.tasks,self.catalog));self.assertEqual(result['complete_agreement'],104)
 def test_old_review_columns_rejected(self):
  path=self.form();path.write_text(path.read_text().replace('review_input_sha256,','',1))
  with self.assertRaisesRegex(ValueError,'COLUMNS'):read_form(path,self.tasks)
 def test_stale_binding_rejected_without_output(self):
  a=self.form(change=lambda rows:rows[0].update(review_input_sha256='0'*64));b=self.form('b.csv','synthetic-B');out=self.root/'out.json'
  with self.assertRaisesRegex(ValueError,'BINDING'):compare(a,b,out)
  self.assertFalse(out.exists())
 def test_task_catalog_and_contract_changes_change_identity(self):
  before=review_identity(self.tasks,self.catalog);tasks=copy.deepcopy(self.tasks);tasks[0]['prompt']+=' changed'
  self.assertNotEqual(digest(before),digest(review_identity(tasks,self.catalog)))
  catalog=copy.deepcopy(self.catalog);catalog['cycle']='changed';self.assertNotEqual(digest(before),digest(review_identity(self.tasks,catalog)))
  with patch('cardiobench.review.CONTRACT_VERSION','next'):self.assertNotEqual(digest(before),digest(review_identity(self.tasks,self.catalog)))
 def copy_core(self):
  dest=self.root/'release';dest.mkdir()
  for name in [*read_json(ROOT/'MANIFEST_SHA256.json')['files'],'MANIFEST_SHA256.json']:
   source=ROOT/name;target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
  return dest
 def test_unverified_task_edits_fail_review_cli(self):
  a=self.form();b=self.form('b.csv','synthetic-B');dest=self.copy_core();path=dest/'cardiobench/data/tasks.json';tasks=read_json(path);tasks[0]['prompt']+=' changed';path.write_text(json.dumps(tasks))
  done=subprocess.run([sys.executable,'-m','cardiobench.review','--reviewer-a',str(a),'--reviewer-b',str(b),'--out',str(self.root/'out.json')],cwd=dest,text=True,capture_output=True)
  self.assertEqual(done.returncode,2);self.assertIn('DISTRIBUTION_HASH_MISMATCH',done.stderr);self.assertFalse((self.root/'out.json').exists())
 def test_rehashed_new_release_still_rejects_old_forms(self):
  a=self.form();b=self.form('b.csv','synthetic-B');dest=self.copy_core();path=dest/'cardiobench/data/tasks.json';tasks=read_json(path);tasks[0]['prompt']+=' changed';path.write_text(json.dumps(tasks))
  manifest=read_json(dest/'MANIFEST_SHA256.json');manifest['files']['cardiobench/data/tasks.json']=sha(path);(dest/'MANIFEST_SHA256.json').write_text(json.dumps(manifest))
  done=subprocess.run([sys.executable,'-m','cardiobench.review','--reviewer-a',str(a),'--reviewer-b',str(b),'--out',str(self.root/'out.json')],cwd=dest,text=True,capture_output=True)
  self.assertEqual(done.returncode,2);self.assertIn('REVIEW_INPUT_BINDING_MISMATCH',done.stderr)
 def test_long_csv_field_is_controlled_and_restores_limit(self):
  before=csv.field_size_limit();path=self.form(change=lambda rows:rows[0].update(evidence_rationale='x'*140000))
  with self.assertRaisesRegex(ValueError,'REVIEW_CSV_ERROR'):read_form(path,self.tasks)
  self.assertEqual(csv.field_size_limit(),before)
 def test_long_csv_cli_no_traceback_or_output(self):
  a=self.form(change=lambda rows:rows[0].update(evidence_rationale='x'*140000));b=self.form('b.csv','synthetic-B');out=self.root/'out.json'
  done=subprocess.run([sys.executable,'-m','cardiobench.review','--reviewer-a',str(a),'--reviewer-b',str(b),'--out',str(out)],cwd=ROOT,capture_output=True,text=True)
  self.assertEqual(done.returncode,2);self.assertIn('REVIEW_CSV_ERROR',done.stderr);self.assertNotIn('Traceback',done.stderr);self.assertFalse(out.exists())
 def test_csv_field_at_limit_is_accepted(self):
  rows,_=read_form(self.form(change=lambda rows:rows[0].update(evidence_rationale='x'*MAX_FIELD_CHARS)),self.tasks);self.assertEqual(len(rows['S01']['evidence_rationale']),MAX_FIELD_CHARS)
 def test_csv_file_limit(self):
  path=self.root/'large.csv';path.write_bytes(b'x'*(MAX_FILE_BYTES+1))
  with self.assertRaisesRegex(ValueError,'FILE_TOO_LARGE'):read_form(path,self.tasks)
 def test_csv_response_byte_limit(self):
  def change(rows):
   response=copy.deepcopy(self.gold['S01']);response['answer']['variable']='中'*23000;rows[0]['proposed_response_json']=json.dumps(response,ensure_ascii=False)
  with self.assertRaisesRegex(ValueError,'RESPONSE_TOO_LARGE'):read_form(self.form(change=change),self.tasks)
 def test_csv_malformed_quote_is_controlled(self):
  path=self.root/'bad.csv';path.write_text(','.join(COLUMNS)+'\n"unterminated')
  with self.assertRaisesRegex(ValueError,'CSV_ERROR'):read_form(path,self.tasks)
 def test_csv_invalid_utf8_is_controlled(self):
  path=self.root/'bad.csv';path.write_bytes(b'\xff')
  with self.assertRaisesRegex(ValueError,'INVALID_UTF8'):read_form(path,self.tasks)
 def test_csv_quoted_newline_rationale_retained(self):
  rows,_=read_form(self.form(change=lambda rows:rows[0].update(evidence_rationale='Line 1, cited\nLine "2"')),self.tasks);self.assertEqual(rows['S01']['evidence_rationale'],'Line 1, cited\nLine "2"')
 def test_reused_w11_id_does_not_inherit_policy(self):
  task=self.task('S01');task['id']='W11';response=copy.deepcopy(self.gold['S01']);response['evidence']=['TRIGLY_J:WTSAF2YR','WEIGHTING:SELECTION']
  result=summarize([task],{'W11':self.gold['S01']},{'W11':response});row=result['policy_adjusted']['rows'][0]
  self.assertFalse(row['joint_correct']);self.assertFalse(row['alternative_policy_applicable'])
 def test_modified_w11_request_loses_policy(self):
  task=self.task('W11');task['request']['files']=['GLU_J'];response=copy.deepcopy(self.gold['W11']);response['evidence']=['TRIGLY_J:WTSAF2YR','WEIGHTING:SELECTION']
  self.assertFalse(summarize([task],self.gold,{'W11':response})['policy_adjusted']['rows'][0]['joint_correct'])
 def test_current_w11_policy_kept(self):
  task=self.task('W11');response=copy.deepcopy(self.gold['W11']);response['evidence']=['TRIGLY_J:WTSAF2YR','WEIGHTING:SELECTION'];result=summarize([task],self.gold,{'W11':response})
  self.assertEqual(result['overall']['joint_correct'],0);self.assertEqual(result['policy_adjusted']['overall']['joint_correct'],1)
 def test_grade_two_argument_calls_fail_explicitly(self):
  with self.assertRaises(TypeError):grade(self.gold['C15'],self.gold['C15'])
  with self.assertRaisesRegex(ValueError,'TASK_REQUIRED'):grade(self.gold['C15'],self.gold['C15'],None)
 def test_conversion_string_schema_not_answer_mismatch(self):
  task=self.task('C15');response=copy.deepcopy(self.gold['C15']);response['answer']['values']=['1'];result=grade(response,self.gold['C15'],task)
  self.assertFalse(result['schema_valid']);self.assertIn('INVALID_FIELD_TYPE',result['error'])
 def test_abstention_gold_does_not_determine_answer_schema(self):
  result=grade(self.gold['W01'],self.gold['W14'],self.task('W14'));self.assertTrue(result['schema_valid']);self.assertEqual(result['error'],'ANSWER_MISMATCH')
 def test_clean_nonfinite_strings_rejected_in_both_paths(self):
  for value in ['NaN','sNaN','Infinity','-Inf',' nan ']:
   task=next(copy.deepcopy(t) for t in self.tasks if t['kind']=='coding' and t['request']['operation']=='clean');task['request']['values']=[value]
   with self.subTest(value=value),self.assertRaisesRegex(ValueError,'INVALID_CODE_VALUE'):validate_tasks([task],self.gold)
   with self.subTest(value=value),self.assertRaisesRegex(ValueError,'INVALID_CODE_VALUE'):reference(task,self.catalog)
 def test_clean_text_and_literal_missing_retained_correctly(self):
  task=next(copy.deepcopy(t) for t in self.tasks if t['kind']=='coding' and t['request']['operation']=='clean' and t['request']['variable']=='RIDAGEYR');task['request']['values']=['text','.',7,'7.0',None]
  validate_tasks([task],self.gold);self.assertEqual(reference(task,self.catalog)['answer']['values'],['text',None,7,'7.0',None])
 def test_same_column_name_on_opposite_sides_valid(self):
  task=self.task('E01');r=task['request'];old=r['value_column'];r['value_column']=r['age_column']
  for row in r['right']:row[r['value_column']]=row.pop(old)
  answer=execute_fixture(r);self.assertEqual(answer,self.gold['E01']['answer']);validate_tasks([task],{'E01':{**self.gold['E01'],'answer':answer}})
 def test_invalid_fixture_uses_runtime_validation_reason(self):
  task=self.task('E01');task['request']['left'][0][task['request']['age_column']]=None
  for fn in [lambda:validate_tasks([task],self.gold),lambda:execute_fixture(task['request'])]:
   with self.assertRaisesRegex(ValueError,'INVALID_AGE'):fn()
 def test_rejection_fixtures_still_allowed(self):
  cases=[t for t in self.tasks if t['kind']=='execution' and self.gold[t['id']]['status']=='reject'];validate_tasks(cases,self.gold);self.assertTrue(cases)

 def bundle(self):
  from delivery_fixture import populate
  root=self.root/'bundle';root.mkdir();(root/'packages').mkdir()
  data=root/'cardiobench/data';data.mkdir(parents=True)
  for path in DATA.glob('*.json'):(data/path.name).write_bytes(path.read_bytes())
  for path in (ROOT/'cardiobench').glob('*.py'):(root/'cardiobench'/path.name).write_bytes(path.read_bytes())
  shutil.copy2(ROOT/'requirements-build.txt',root/'requirements-build.txt')
  (root/'sources').mkdir();shutil.copy2(ROOT/'sources/manifest.json',root/'sources/manifest.json')
  (root/'examples').mkdir();shutil.copy2(ROOT/'examples/trusted_reference_adapter.py',root/'examples/trusted_reference_adapter.py')
  files={p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}
  (root/'MANIFEST_SHA256.json').write_text(json.dumps({'version':__version__,'algorithm':'sha256','files':files}))
  self.package(root,'wheel');self.package(root,'sdist');populate(root,self.tasks,self.gold,self.catalog)
  self.refreeze(root);return root
 def package(self,root,kind,version=None,changed=None):
  version=version or __version__;manifest=read_json(root/'MANIFEST_SHA256.json');core={name:(root/name).read_bytes() for name in manifest['files']};core['MANIFEST_SHA256.json']=(root/'MANIFEST_SHA256.json').read_bytes()
  metadata=('Metadata-Version: 2.1\nName: nhanes-cardiobench\nVersion: '+version+'\nRequires-Python: >=3.10\n').encode()
  if kind=='wheel':
   path=root/('packages/nhanes_cardiobench-'+__version__+'-py3-none-any.whl');members={name if name.startswith('cardiobench/') else 'cardiobench/_release/'+name:data for name,data in core.items()};members['nhanes_cardiobench-'+__version__+'.dist-info/METADATA']=metadata
   folder='nhanes_cardiobench-'+__version__+'.dist-info'
   members[folder+'/WHEEL']=b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
   members[folder+'/entry_points.txt']=b'[console_scripts]\ncardiobench = cardiobench.__main__:main\n'
   if changed:changed(members)
   import base64
   stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n')
   for name,data in members.items():writer.writerow([name,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(),len(data)])
   writer.writerow([folder+'/RECORD','','']);members[folder+'/RECORD']=stream.getvalue().encode()
   with zipfile.ZipFile(path,'w') as z:
    for name,data in members.items():z.writestr(name,data)
  else:
   path=root/('packages/nhanes_cardiobench-'+__version__+'.tar.gz');members={'nhanes_cardiobench-'+__version__+'/'+name:data for name,data in core.items()};members['nhanes_cardiobench-'+__version__+'/PKG-INFO']=metadata
   if changed:changed(members)
   with tarfile.open(path,'w:gz') as z:
    for name,data in members.items():info=tarfile.TarInfo(name);info.size=len(data);z.addfile(info,io.BytesIO(data))
  return path
 def refreeze(self,root):
  (root/'ARTIFACTS_SHA256.json').write_text(json.dumps({'version':__version__,'profile':PROFILE,'algorithm':'sha256','core_manifest_sha256':sha(root/'MANIFEST_SHA256.json'),'files':inventory(root)}))
 def test_matching_delivery_profile_accepts(self):self.assertEqual(verify_artifacts(self.bundle(),True)['profile'],PROFILE)
 def test_rehashed_missing_packages_reject(self):
  root=self.bundle();shutil.rmtree(root/'packages');self.refreeze(root)
  with self.assertRaisesRegex(ValueError,'PACKAGES_MISSING'):verify_artifacts(root,True)
 def test_rehashed_stale_wheel_rejects_metadata(self):
  root=self.bundle();self.package(root,'wheel','0.4.0');self.refreeze(root)
  with self.assertRaisesRegex(ValueError,'PACKAGE_VERSION'):verify_artifacts(root,True)
 def test_rehashed_stale_sdist_rejects_metadata(self):
  root=self.bundle();self.package(root,'sdist','0.4.0');self.refreeze(root)
  with self.assertRaisesRegex(ValueError,'PACKAGE_VERSION'):verify_artifacts(root,True)
 def test_matching_version_stale_embedded_manifest_rejects(self):
  root=self.bundle();path=self.package(root,'wheel',changed=lambda m:m.update({'cardiobench/_release/MANIFEST_SHA256.json':b'{}'}))
  with self.assertRaisesRegex(ValueError,'CORE_MANIFEST'):validate_package(path,root)
 def test_matching_manifest_but_modified_core_code_rejects(self):
  root=self.bundle();path=self.package(root,'wheel',changed=lambda m:m.update({'cardiobench/__init__.py':b'modified'}))
  with self.assertRaisesRegex(ValueError,'CORE_FILE'):validate_package(path,root)
 def test_missing_required_review_material_rejects_after_rehash(self):
  root=self.bundle();(root/'review_materials/reviewer_A.csv').unlink();self.refreeze(root)
  with self.assertRaisesRegex(ValueError,'REQUIRED_DELIVERY'):verify_artifacts(root,True)
 def test_stale_installation_report_rejects_after_rehash(self):
  root=self.bundle();p=root/'validation/installation.json';v=read_json(p);v['package']['sha256']='0'*64;p.write_text(json.dumps(v));self.refreeze(root)
  with self.assertRaisesRegex(ValueError,'INSTALLATION_EVIDENCE'):verify_artifacts(root,True)
 def test_stale_review_inputs_reject_after_rehash(self):
  root=self.bundle();p=root/'review_materials/reviewer_inputs.json';v=read_json(p);v['tasks'][0]['prompt']+='changed';p.write_text(json.dumps(v));self.refreeze(root)
  with self.assertRaisesRegex(ValueError,'REVIEW_MATERIAL'):verify_artifacts(root,True)
 def test_extra_package_is_rejected(self):
  root=self.bundle();(root/'packages/extra.whl').write_bytes(b'old')
  with self.assertRaisesRegex(ValueError,'EXPECTED_ONE'):validate_packages(root)
