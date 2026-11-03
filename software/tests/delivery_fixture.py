"""Synthetic delivery records for validator tests, never release execution evidence."""
from pathlib import Path
from types import SimpleNamespace
import json,csv,copy,base64
from cardiobench import __version__
from cardiobench.core import ROOT
from cardiobench.runner import canonical,digest,file_hash,binding,request_payload,report_documents
from cardiobench.contracts import CONTRACT_VERSION,candidate_contract
from cardiobench.review import COLUMNS,ADJUDICATION_COLUMNS,REVIEW_README
from cardiobench.delivery_evidence import delivery_identity,run_summary,strict_counts
from cardiobench.artifacts import validate_packages

def write(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))
def csvwrite(path,columns,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('w',encoding='utf-8',newline='') as f:w=csv.writer(f);w.writerow(columns);w.writerows(rows)
def populate(root,tasks,gold,catalog):
 identity=delivery_identity(root);folder=root/'validation';review=root/'review_materials';packages=validate_packages(root)
 from cardiobench.installation_evidence import expected_observations,FORMAT_VERSION
 verification,reproduction,parsed=expected_observations(root)
 from cardiobench.build_environment import requirements
 pinned,requirements_sha=requirements(root)
 builder={'python':'synthetic fixture','python_executable':'/synthetic/python','tools':{'pip':'24.0',**pinned},'requirements_sha256':requirements_sha}
 checks=[]
 for name,command,result in [
  ('module_verify',['synthetic-python','-m','cardiobench','verify'],verification),
  ('module_reproduce',['synthetic-python','-m','cardiobench','reproduce','--out','synthetic-output'],{**reproduction,'out':'synthetic-output'}),
  ('source_parse',['synthetic-python','-m','cardiobench.sources'],parsed),
  ('console_help',['synthetic-cardiobench','--help'],'usage: verify reproduce run-adapter --help'),
  ('console_verify',['synthetic-cardiobench','verify'],verification),
  ('console_reproduce',['synthetic-cardiobench','reproduce','--out','synthetic-output'],{**reproduction,'out':'synthetic-output'})]:
  checks.append({'id':name,'command':command,'returncode':0,'stdout':result if isinstance(result,str) else json.dumps(result),'stderr':''})
 for name,kind in [('installation.json','wheel'),('sdist_build.json','sdist')]:
  report={'report_format_version':FORMAT_VERSION,'builder_environment':builder,'status':'passed','version':__version__,'package':packages[kind],'module_version':__version__,'installed_version':__version__,
   'python':'synthetic fixture','platform':'synthetic fixture','python_executable':'synthetic-python','console_executable':'synthetic-cardiobench','checks':checks,'installed_core_manifest_sha256':identity['core_manifest_sha256']}
  if kind=='sdist':report.update(rebuilt_wheel={**packages['wheel'],'filename':'nhanes_cardiobench-'+__version__+'-py3-none-any.whl'},
   build_command=['/synthetic/python','-m','pip','wheel','--no-index','--no-build-isolation','--no-deps','--wheel-dir','synthetic-wheel','synthetic-source'],build_returncode=0,build_stdout='synthetic fixture, not an observed build',build_stderr='')
  write(folder/name,report)
 from cardiobench.verification_evidence import test_method_count
 write(folder/'release_gate.json',{'status':'passed','version':__version__,'evidence_binding':identity,'scope':'core staging gate','test_methods':test_method_count(root),**verification})
 contracts={t['id']:candidate_contract(t) for t in tasks}
 commitment={'review_format_version':'2','suite_version':__version__,'contract_version':CONTRACT_VERSION,'core_manifest_sha256':identity['core_manifest_sha256'],'release_sha256':identity['input_hashes']['release.json'],'tasks_sha256':digest(tasks),'catalog_sha256':digest(catalog),'response_contracts_sha256':digest(contracts)}
 write(review/'reviewer_inputs.json',{'version':__version__,'contract_version':CONTRACT_VERSION,'review_input_identity':commitment,'review_input_sha256':digest(commitment),'tasks':tasks,'catalog':catalog,'response_contracts':contracts,'input_hashes':{n:identity['input_hashes'][n] for n in ('tasks.json','catalog.json')}})
 for name in ['reviewer_A.csv','reviewer_B.csv']:csvwrite(review/name,COLUMNS,[[t['id'],digest(commitment),'','','','',''] for t in tasks])
 csvwrite(review/'adjudication.csv',ADJUDICATION_COLUMNS,[[t['id'],'pending','','','',''] for t in tasks])
 write(review/'expected_answers_after_review.json',gold);(review/'README.txt').write_text(REVIEW_README,encoding='utf-8')
 selected=[t for t in tasks if t['split']=='development'];args=SimpleNamespace(adapter=str(ROOT/'examples/trusted_reference_adapter.py'),prompt_file=None,disclosure=None,track='provided-context',timeout=30,stdout_limit=1000000,stderr_limit=64000)
 bound,_=binding(args,selected,catalog,gold)
 state={'run_id':'12345678-1234-5678-1234-567812345678','created_utc':'2026-10-21T00:00:00+00:00','updated_utc':'2026-10-21T00:00:00+00:00','binding':bound,'records':[]}
 for t in selected:
  payload=request_payload(t,catalog,bound);write(folder/'resume_run/requests'/(t['id']+'.json'),payload);raw=canonical(gold[t['id']]);attempt={'started_utc':state['created_utc'],'request_sha256':digest(payload),'response':gold[t['id']],'stdout':raw.decode(),'stderr':'','error':None,'seconds':0.1,'returncode':0}
  for key,data in [('stdout',raw),('stderr',b'')]:
   import hashlib
   attempt.update({key+'_sha256':hashlib.sha256(data).hexdigest(),key+'_retained_bytes':len(data),key+'_base64':base64.b64encode(data).decode()})
  state['records'].append({'id':t['id'],'attempts':[attempt]})
 first=copy.deepcopy(state);first['records']=first['records'][:5]
 write(folder/'resume_first_checkpoint.json',{'state':first,'sha256':digest(first)});write(folder/'resume_run/checkpoint.json',{'state':state,'sha256':digest(state)})
 for name,value in report_documents(state,selected,gold).items():write(folder/'resume_run'/name,value)
 final_hash=file_hash(folder/'resume_run/checkpoint.json');n=len(selected)
 write(folder/'resume_validation.json',{'version':__version__,'status':'passed','evidence_binding':identity,'first':run_summary(first,n),'resumed':run_summary(state,n),'completed_resume':run_summary(state,n),'final_joint_correct':n,'final_attempts':n,'completed_checkpoint_unchanged':True,'checkpoint_sha256':final_hash,'completed_resume_before_sha256':final_hash,'first_checkpoint_sha256':file_hash(folder/'resume_first_checkpoint.json')})
 from cardiobench.core import run_builtin,reference,lexical,lexical_context,environment
 from cardiobench.reproduction_evidence import deterministic_report,check_csv,TIMING_SCOPE
 sem=[t for t in tasks if t['kind']=='semantic'];pred,_=run_builtin(tasks,catalog,reference);lex,_=run_builtin(sem,catalog,lexical);context,_=run_builtin(sem,catalog,lexical_context)
 paper=deterministic_report(root,tasks,gold,pred,lex,context)
 paper.update(verification=verification,environment=environment(),timing={'reference_first_seconds':0.1,'lexical_seconds':0.1,'context_lexical_seconds':0.1,'warm_reference_repeats':30,'warm_reference_raw_seconds':[0.1]*30,'warm_reference_median_seconds':0.1,'warm_reference_min_seconds':0.1,'warm_reference_max_seconds':0.1,'scope':TIMING_SCOPE})
 for name,value in [('paper_results.json',paper),('reference_predictions.json',pred),('lexical_predictions.json',lex),('context_lexical_predictions.json',context)]:write(folder/'process_reproduction'/name,value)
 (folder/'process_reproduction/check_results.csv').write_bytes(check_csv(paper['reference']))
 from cardiobench.process_evidence import FORMAT_VERSION as PROCESS_FORMAT,SCOPE
 result={'reference':paper['reference']['overall'],'lexical_semantic':paper['lexical']['overall'],'mutations':{k:v for k,v in paper['mutations'].items() if k!='rows'},'out':'/synthetic/output'}
 write(folder/'process_timing.json',{'report_format_version':PROCESS_FORMAT,'version':__version__,'evidence_binding':identity,'seconds':4.0,'python_executable':'/synthetic/python','output_directory':'/synthetic/output','command':['/synthetic/python','-m','cardiobench','reproduce','--out','/synthetic/output'],'returncode':0,'stdout':json.dumps(result),'stderr':'','scope':SCOPE,'verification_scope':'not bundled','paper_results_sha256':file_hash(folder/'process_reproduction/paper_results.json'),'result':result})
