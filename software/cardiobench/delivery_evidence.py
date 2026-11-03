"""Semantic consistency of staged evidence; operator records are not attestations."""
from pathlib import Path
import csv,io,math
from . import __version__
from .core import read_json,grade
from .runner import digest,file_hash,validate_state,request_payload,report_documents
from .contracts import CONTRACT_VERSION,candidate_contract
from .review import COLUMNS,ADJUDICATION_COLUMNS,REVIEW_README,MAX_FILE_BYTES,MAX_FIELD_CHARS

INPUTS=('tasks.json','gold.json','catalog.json','release.json','positive_control_routes.json','evidence_policy.json')
def delivery_identity(root):
    root=Path(root)
    return {'version':__version__,'core_manifest_sha256':file_hash(root/'MANIFEST_SHA256.json'),
            'input_hashes':{name:file_hash(root/'cardiobench/data'/name) for name in INPUTS}}

def require(ok,message):
    if not ok:raise ValueError(message)

def object_at(path):
    value=read_json(path)
    require(isinstance(value,dict),'INVALID_EVIDENCE_OBJECT: '+str(path))
    return value

def table(path,columns):
    raw=Path(path).read_bytes();require(len(raw)<=MAX_FILE_BYTES,'REVIEW_MATERIAL_TOO_LARGE')
    try:
        from .review import _CSV_LOCK
        with _CSV_LOCK:
            previous=csv.field_size_limit(MAX_FIELD_CHARS)
            try:
                reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True)
                rows=list(reader)
            finally:csv.field_size_limit(previous)
    except (UnicodeDecodeError,csv.Error) as exc:raise ValueError('INVALID_REVIEW_MATERIAL: '+str(exc)) from None
    require(reader.fieldnames==columns and all(set(row)==set(columns) and all(v is not None for v in row.values()) for row in rows),'REVIEW_MATERIAL_COLUMNS_MISMATCH')
    return rows

def validate_review(root,tasks,gold,catalog,identity):
    folder=root/'review_materials';inputs=object_at(folder/'reviewer_inputs.json')
    contracts={t['id']:candidate_contract(t) for t in tasks}
    expected={'review_format_version':'2','suite_version':__version__,'contract_version':CONTRACT_VERSION,
      'core_manifest_sha256':identity['core_manifest_sha256'],'release_sha256':identity['input_hashes']['release.json'],
      'tasks_sha256':digest(tasks),'catalog_sha256':digest(catalog),'response_contracts_sha256':digest(contracts)}
    require(inputs.get('version')==__version__ and inputs.get('contract_version')==CONTRACT_VERSION and
      inputs.get('review_input_identity')==expected and inputs.get('review_input_sha256')==digest(expected) and
      digest(inputs.get('tasks'))==digest(tasks) and digest(inputs.get('catalog'))==digest(catalog) and
      digest(inputs.get('response_contracts'))==digest(contracts) and
      inputs.get('input_hashes')=={name:identity['input_hashes'][name] for name in ('tasks.json','catalog.json')},'REVIEW_MATERIAL_BINDING_MISMATCH')
    ids=[t['id'] for t in tasks]
    for name in ('reviewer_A.csv','reviewer_B.csv'):
        rows=table(folder/name,COLUMNS)
        require([r['task_id'] for r in rows]==ids and all(r['review_input_sha256']==digest(expected) and all(r[k]=='' for k in COLUMNS[2:]) for r in rows),'REVIEW_MATERIAL_BINDING_MISMATCH: blank current forms required')
    answers=object_at(folder/'expected_answers_after_review.json')
    require(digest(answers)==digest(gold),'REVIEW_EXPECTED_ANSWERS_MISMATCH')
    rows=table(folder/'adjudication.csv',ADJUDICATION_COLUMNS)
    require([r['task_id'] for r in rows]==ids and all(r['status']=='pending' and all(r[k]=='' for k in ADJUDICATION_COLUMNS[2:]) for r in rows),'REVIEW_ADJUDICATION_MISMATCH: pending preparation required')
    require((folder/'README.txt').read_text(encoding='utf-8')==REVIEW_README,'REVIEW_INSTRUCTIONS_MISMATCH')

def strict_counts(tasks,gold,predictions):
    require(isinstance(predictions,dict) and set(predictions)=={t['id'] for t in tasks},'EVIDENCE_PREDICTION_SELECTION_MISMATCH')
    rows=[grade(predictions[t['id']],gold[t['id']],t) for t in tasks]
    return {'checks':len(tasks),**{key:sum(r[key] for r in rows) for key in ('joint_correct','answer_correct','evidence_correct','schema_valid')}}

def run_summary(state,total):
    rows=state['records']
    return {'run_id':state['run_id'],'binding_sha256':digest(state['binding']),'completed_cases':len(rows),
      'total_cases':total,'status':'complete' if len(rows)==total else 'partial','failed_cases':0,
      'execution_failed_cases':0,'format_failed_cases':0,'incorrect_answer_cases':0,'evidence_mismatch_cases':0,
      'error_counts':{},'total_attempts':sum(len(row['attempts']) for row in rows)}

def validate_resume(root,tasks,gold,catalog,identity):
    folder=root/'validation';report=object_at(folder/'resume_validation.json')
    require(report.get('version')==__version__ and report.get('status')=='passed' and report.get('evidence_binding')==identity,'RESUME_EVIDENCE_BINDING_MISMATCH')
    selected=[t for t in tasks if t['split']=='development'];ids=[t['id'] for t in selected];total=len(ids)
    require(total>=5,'RESUME_SELECTION_TOO_SMALL')
    states=[]
    for name in ('resume_first_checkpoint.json','resume_run/checkpoint.json'):
        envelope=object_at(folder/name);state=envelope.get('state');require(isinstance(state,dict),'INVALID_CHECKPOINT')
        binding=state.get('binding');require(isinstance(binding,dict),'INVALID_CHECKPOINT_BINDING')
        expected={'schema_version':4,'contract_version':CONTRACT_VERSION,'suite_version':__version__,
          'task_ids':ids,'tasks_sha256':digest(selected),'catalog_sha256':digest(catalog),
          'scoring_gold_sha256':digest(gold),'gold_file_sha256':identity['input_hashes']['gold.json'],
          'evidence_policy_sha256':identity['input_hashes']['evidence_policy.json'],
          'response_task_types':{t['id']:{'kind':t['kind'],'request':{'operation':t['request'].get('operation')}} for t in selected},
          'runner_source_sha256':{p.name:file_hash(p) for p in sorted((root/'cardiobench').glob('*.py'))},
          'adapter_sha256':file_hash(root/'examples/trusted_reference_adapter.py'),'track':'provided-context','prompt_text':None}
        require(all(binding.get(k)==v for k,v in expected.items()),'RESUME_CHECKPOINT_BINDING_MISMATCH')
        from .binding_contract import validate_binding
        validate_binding(binding,selected)
        validate_state(envelope,binding)
        by_id={t['id']:t for t in selected}
        for row in state['records']:
            require(len(row['attempts'])==1 and row['attempts'][0]['error'] is None,'RESUME_CONTROL_ATTEMPT_MISMATCH')
            attempt=row['attempts'][0];tid=row['id']
            require(grade(attempt['response'],gold[tid],by_id[tid])['joint_correct'],'RESUME_CONTROL_SCORE_MISMATCH')
            expected_hash=digest(request_payload(by_id[tid],catalog,binding))
            require(attempt['request_sha256']==expected_hash and file_hash(folder/'resume_run/requests'/(tid+'.json'))==expected_hash,'RESUME_REQUEST_ARCHIVE_MISMATCH')
        states.append(state)
    first,final=states
    for name,value in report_documents(final,selected,gold).items():
        require(digest(read_json(folder/'resume_run'/name))==digest(value),'RESUME_DERIVED_REPORT_MISMATCH: '+name)
    require([r['id'] for r in first['records']]==ids[:5] and [r['id'] for r in final['records']]==ids and
      first['records']==final['records'][:5] and first['run_id']==final['run_id'] and first['binding']==final['binding'] and
      first['created_utc']==final['created_utc'],'RESUME_HISTORY_MISMATCH')
    final_hash=file_hash(folder/'resume_run/checkpoint.json')
    require(digest(report.get('first'))==digest(run_summary(first,total)) and digest(report.get('resumed'))==digest(run_summary(final,total)) and
      digest(report.get('completed_resume'))==digest(run_summary(final,total)) and type(report.get('final_joint_correct')) is int and
      report['final_joint_correct']==total and type(report.get('final_attempts')) is int and report['final_attempts']==total and
      report.get('completed_checkpoint_unchanged') is True and report.get('checkpoint_sha256')==final_hash and
      report.get('completed_resume_before_sha256')==final_hash and report.get('first_checkpoint_sha256')==file_hash(folder/'resume_first_checkpoint.json'),'RESUME_RESULT_MISMATCH')

def validate_process(root,tasks,gold,identity):
    folder=root/'validation';report=object_at(folder/'process_timing.json');seconds=report.get('seconds')
    require(report.get('version')==__version__ and report.get('evidence_binding')==identity,'PROCESS_EVIDENCE_BINDING_MISMATCH')
    from .binding_contract import positive_finite
    require(positive_finite(seconds),'INVALID_PROCESS_SECONDS')
    paper_path=folder/'process_reproduction/paper_results.json';paper=object_at(paper_path)
    require(report.get('paper_results_sha256')==file_hash(paper_path) and paper.get('version')==__version__ and
      paper.get('input_hashes')==identity['input_hashes'] and isinstance(paper.get('verification'),dict) and
      paper['verification'].get('core_manifest_sha256')==identity['core_manifest_sha256'],'PROCESS_RESULT_BINDING_MISMATCH')
    from .reproduction_evidence import validate_reproduction
    validate_reproduction(root,paper_path.parent,tasks,gold,read_json(root/'cardiobench/data/catalog.json'))
    require(report.get('verification_scope') in ('not bundled','verified') and
      report['verification_scope']==paper['verification'].get('artifact_verification',{}).get('status'),'PROCESS_VERIFICATION_SCOPE_MISMATCH')
    reference=strict_counts(tasks,gold,object_at(folder/'process_reproduction/reference_predictions.json'))
    semantic=[t for t in tasks if t['kind']=='semantic']
    lexical=strict_counts(semantic,gold,object_at(folder/'process_reproduction/lexical_predictions.json'))
    require(reference['joint_correct']==len(tasks) and isinstance(paper.get('reference'),dict) and
      paper['reference'].get('overall')==reference and isinstance(paper.get('lexical'),dict) and
      paper['lexical'].get('overall')==lexical,'PROCESS_SCORE_MISMATCH')
    mutation=paper.get('mutations');require(isinstance(mutation,dict),'PROCESS_MUTATION_MISMATCH')
    rows=mutation.get('rows');n=3*len(tasks)
    require(isinstance(rows,list) and len(rows)==n and {(r.get('id'),r.get('mutation')) for r in rows if isinstance(r,dict)}=={(t['id'],kind) for t in tasks for kind in ('content','evidence','status')} and
      all(isinstance(r,dict) and r.get('schema_valid') is True and r.get('detected') is True for r in rows) and
      mutation.get('mutation_protocol_version')=='1.1' and mutation.get('perturbed_records')==n and mutation.get('detected')==n and mutation.get('schema_valid_records')==n and mutation.get('all_detected') is True,'PROCESS_MUTATION_MISMATCH')
    from .process_evidence import validate_process_record
    validate_process_record(report,paper['timing'])
    expected={'reference':reference,'lexical_semantic':lexical,'mutations':{k:v for k,v in mutation.items() if k!='rows'},'out':report['output_directory']}
    result=report.get('result');require(isinstance(result,dict) and digest(result)==digest(expected),'PROCESS_SUMMARY_MISMATCH')

def validate_evidence(root):
    root=Path(root);data=root/'cardiobench/data';tasks=read_json(data/'tasks.json');gold=read_json(data/'gold.json');catalog=read_json(data/'catalog.json')
    identity=delivery_identity(root);gate=object_at(root/'validation/release_gate.json')
    from .verification_evidence import validate_staging_gate
    validate_staging_gate(root,gate,identity)
    validate_review(root,tasks,gold,catalog,identity)
    validate_resume(root,tasks,gold,catalog,identity)
    validate_process(root,tasks,gold,identity)
