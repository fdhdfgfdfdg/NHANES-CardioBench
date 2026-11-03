"""Candidate-visible contracts and shared preflight validation; contains no answers."""
import math,re
from datetime import datetime
from . import __version__

KINDS={'semantic','coding','weights','leakage','execution'}
ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}')
DEVICE_ID=re.compile(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$',re.I)

def validate_task_ids(tasks):
    seen=set();folded=set()
    for task in tasks:
        tid=task.get('id') if isinstance(task,dict) else None
        if not isinstance(tid,str) or ID.fullmatch(tid) is None:raise ValueError('INVALID_TASK_ID')
        if DEVICE_ID.fullmatch(tid):raise ValueError('RESERVED_TASK_ID')
        if tid in seen:raise ValueError('DUPLICATE_TASK_ID')
        if tid.casefold() in folded:raise ValueError('CASE_COLLIDING_TASK_ID')
        seen.add(tid);folded.add(tid.casefold())
REASONS={
 'CYCLE_OUT_OF_SCOPE':'Requested cycle is not in the preserved corpus.',
 'NOT_IN_RELEASE':'Requested variable or component is absent from the release.',
 'UNIT_NOT_CURATED':'The variable exists but its unit is not curated.',
 'JOINT_WEIGHT_NOT_SPECIFIED':'Joint fasting/dietary adjustment has not been supplied.',
 'CYCLIC_DEPENDENCY':'Declared dependency graph contains a cycle.',
 'INVALID_FIXTURE':'Fixture must be an object.',
 'FIXTURE_NOT_DECLARED_SYNTHETIC':'synthetic must be true.',
 'MISSING_FIELD':'Required fixture-level field is missing.',
 'INVALID_COLUMN_NAME':'Column name must be a nonempty string.',
 'INVALID_MINIMUM_AGE':'Threshold must be finite, numeric and nonnegative.',
 'INVALID_ROWS':'Each input table must be a list of row objects.',
 'MISSING_COLUMN':'A required row column is missing.',
 'INVALID_KEY':'Join key must be a positive integer, excluding booleans.',
 'DUPLICATE_KEY':'Keys must be unique within each input table.',
 'INVALID_WEIGHT':'A nonmissing weight must be finite, numeric and nonnegative.',
 'INVALID_AGE':'Age must be finite, numeric and nonnegative.',
 'INVALID_VALUE':'A nonmissing outcome must be finite and numeric.',
 'EMPTY_ANALYSIS':'No rows satisfy the stated analysis eligibility rules.',
 'NONFINITE_RESULT':'The final numeric result of conversion or weighted analysis cannot be represented as a finite binary float.',
 'INTEGER_LIMIT_EXCEEDED':'An integer exceeds the 4096 decimal digit input limit.'}
POLICY_IDS=['GLU_J:CONVERSION','WEIGHTING:SELECTION','CORPUS:MANIFEST','POLICY:JOINT_WEIGHT','POLICY:DEPENDENCY','POLICY:EXECUTION']

CONTRACT_VERSION='1.4'
REASONS.update({'INVALID_DEPENDENCY_GRAPH':'Invalid dependency graph structure.', 'GRAPH_LIMIT_EXCEEDED':'Graph exceeds 10000 nodes or 100000 edges.'})

def task_operation(kind,request):
    """Reserve non-null operation values for the three coding operations."""
    if not isinstance(kind,str) or kind not in KINDS:raise ValueError('INVALID_TASK_KIND')
    if not isinstance(request,dict):raise ValueError('INVALID_TASK_REQUEST')
    op=request.get('operation')
    if (kind=='coding' and op not in ('unit','clean','convert_glucose')) or (kind!='coding' and op is not None):
        raise ValueError('INVALID_TASK_OPERATION')
    return op

def response_descriptor(task):
    return {'kind':task['kind'],'request':{'operation':task_operation(task['kind'],task['request'])}}

def answer_spec(task):
    string={'type':'string','minLength':1}
    kind=task['kind'];op=task_operation(kind,task.get('request'))
    if kind=='coding':
        return {'unit':string} if op=='unit' else {'values':{'type':'array','items':{'type':['number','string','null'] if op=='clean' else 'number'}}}
    return {
      'semantic':{'variable':string,'file':string},
      'weights':{'weight':string,'stratum':string,'psu':string},
      'leakage':{'excluded_features':{'type':'array','items':string,'uniqueItems':True}},
      'execution':{'joined_rows':{'type':'integer','minimum':0,'x-integer-token-only':True},'cohort_n':{'type':'integer','minimum':1,'x-integer-token-only':True},'weighted_mean':{'type':'number'}}}[kind]

def check_schema(value,spec,path='answer'):
    def matches(t):
        return {'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),'null':value is None,'integer':type(value) is int,'number':type(value) in (int,float)}[t]
    types=spec.get('type');types=[types] if isinstance(types,str) else types
    if types and not any(matches(t) for t in types):raise ValueError('INVALID_FIELD_TYPE: '+path)
    if 'minimum' in spec and value<spec['minimum']:raise ValueError('FIELD_BELOW_MINIMUM: '+path)
    if 'minLength' in spec and len(value)<spec['minLength']:raise ValueError('EMPTY_FIELD: '+path)
    if isinstance(value,dict):
        fields=spec.get('properties',{})
        if not set(spec.get('required',[]))<=set(value) or (spec.get('additionalProperties') is False and not set(value)<=set(fields)):raise ValueError('ANSWER_FIELDS_MISMATCH: '+path)
        for k,v in value.items():
            if k in fields:check_schema(v,fields[k],path+'.'+k)
    if isinstance(value,list):
        if spec.get('uniqueItems') and len(value)!=len(set(value)):raise ValueError('DUPLICATE_FIELD: '+path)
        for i,v in enumerate(value):check_schema(v,spec['items'],path+'['+str(i)+']')

def validate_task_response(task,response):
    from .core import validate_response
    validate_response(response)
    if response['status']=='answer':
        fields=answer_spec(task)
        check_schema(response['answer'],{'type':'object','properties':fields,'required':list(fields),'additionalProperties':False})
    return response

def task_fingerprint(task):
    import hashlib,json
    return hashlib.sha256(json.dumps(task,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()

def validate_tasks(tasks,gold=None):
    from .core import ensure_finite,validate_graph,validate_clean_values,validate_fixture
    if not isinstance(tasks,list):raise ValueError('INVALID_TASK_SELECTION')
    if not tasks:raise ValueError('EMPTY_TASK_SELECTION')
    ensure_finite(tasks,64);validate_task_ids(tasks);seen=set()
    def text(req,k):
        if not isinstance(req.get(k),str) or not req[k].strip():raise ValueError('INVALID_TASK_REQUEST: '+k)
    for task in tasks:
        if not isinstance(task,dict) or not isinstance(task.get('id'),str) or ID.fullmatch(task['id']) is None:raise ValueError('INVALID_TASK_ID')
        if task['id'] in seen:raise ValueError('DUPLICATE_TASK_ID')
        seen.add(task['id'])
        for key in ('canonical_id','group_id'):
            if not isinstance(task.get(key),str) or ID.fullmatch(task[key]) is None:raise ValueError('INVALID_TASK_FIELD: '+key)
        if not isinstance(task.get('kind'),str) or task['kind'] not in KINDS:raise ValueError('INVALID_TASK_KIND')
        if task.get('split') not in ('development','evaluation'):raise ValueError('INVALID_TASK_SPLIT')
        for key in ('cycle','prompt'):text(task,key)
        req=task.get('request');kind=task['kind']
        if not isinstance(req,dict):raise ValueError('INVALID_TASK_REQUEST')
        op=task_operation(kind,req)
        if kind=='semantic':text(req,'concept')
        elif kind=='coding':
            if op in ('unit','clean'):
                text(req,'file');text(req,'variable')
            if op!='unit':
                if not isinstance(req.get('values'),list):raise ValueError('INVALID_TASK_VALUES')
                if op=='clean':validate_clean_values(req['values'])
                for value in req['values']:
                    if op=='convert_glucose' and type(value) not in (int,float):raise ValueError('INVALID_TASK_VALUES')
                    if op=='clean' and value is not None and type(value) not in (int,float,str):raise ValueError('INVALID_TASK_VALUES')
        elif kind=='weights':
            text(req,'analysis_cycle');files=req.get('files')
            if not isinstance(files,list) or not files or any(not isinstance(x,str) or not x.strip() for x in files) or len(files)!=len(set(files)):raise ValueError('INVALID_TASK_FILES')
        elif kind=='leakage':validate_graph(req.get('label_sources'),req.get('feature_dependencies'))
        if gold is not None:
            if not isinstance(gold,dict) or task['id'] not in gold:raise ValueError('MISSING_SCORING_GOLD')
            expected=gold[task['id']];validate_task_response(task,expected)
            # Deliberately malformed execution fixtures are retained for rejection tests.
            if kind=='execution' and expected['status']=='answer':
                validate_fixture(req)
    return tasks

def candidate_contract(task):
    fields=answer_spec(task);string={'type':'string','minLength':1}
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','type':'object','required':['status','answer','evidence','reason_code'],'additionalProperties':False,
      'properties':{'status':{'enum':['answer','abstain','reject']},'answer':{'type':'object'},'evidence':{'type':'array','items':string,'uniqueItems':True},'reason_code':{'type':['string','null']}},
      'oneOf':[
       {'properties':{'status':{'const':'answer'},'answer':{'type':'object','properties':fields,'required':list(fields),'additionalProperties':False},'reason_code':{'type':'null'}}},
       {'properties':{'status':{'enum':['abstain','reject']},'answer':{'type':'object','maxProperties':0},'reason_code':{'enum':list(REASONS)}}}]}
    return {'contract_version':CONTRACT_VERSION,'response_schema':schema,'reason_codes':REASONS,
      'protocol_constraints':{'maximum_integer_decimal_digits':4096,'integer_environment':'Python int_max_str_digits must be disabled (0) or at least 4096; incompatible settings fail before JSON processing and output creation.','task_id_files':'Reserved Windows device names and case-insensitive duplicate IDs are forbidden.','maximum_response_container_depth':32,'maximum_json_container_depth':128,'integer_token_only':'x-integer-token-only excludes 1.0 and booleans; standard JSON Schema alone does not enforce lexical integer tokens.','nonfinite_numbers':'forbidden','evidence_identifiers':'must not be whitespace-only'},
      'evidence_convention':{'variable_id':'COMPONENT:VARIABLE using uppercase codebook identifiers','policy_ids':POLICY_IDS,'comparison':'Primary exact evidence; separately labelled author-defined alternatives.'},
      'comparison':{'integer_values':'Exact integer token and value; no booleans.','floating_values':{'relative_tolerance':1e-8,'absolute_tolerance':1e-10},'unit_spelling_vocabulary':['mmHg','kg/m2','mg/dL','mmol/L','%','mg'],'arrays':'Order matters. Sort excluded_features; preserve order for values.'},
      'rejection_order':['synthetic declaration','required fixture fields','column names','minimum age','left then right row containers and keys','left row weight then age','right outcomes','empty analysis','finite result']}

TEXT_FIELDS=['system_name_and_exact_version','provider_or_checkpoint','source_access_policy','retry_policy','token_use_and_cost_or_unavailable_reason']
EXTERNAL_TEXT=['seed_and_determinism_status','tool_call_and_context_budget','hardware_and_operating_system','cache_and_warmup_policy','raw_model_request_and_completion_archive']

def validate_disclosure(value,track):
    from .core import ensure_finite
    ensure_finite(value,32)
    if not isinstance(value,dict):raise ValueError('DISCLOSURE_MUST_BE_OBJECT')
    if 'condition' not in value:raise ValueError('INCOMPLETE_DISCLOSURE: condition')
    if value.get('condition')!=track.replace('-','_'):raise ValueError('DISCLOSURE_TRACK_MISMATCH')
    def filled(key):
        item=value.get(key)
        if not isinstance(item,str) or not item.strip() or 'AUTHOR_TO_COMPLETE' in item:raise ValueError('INCOMPLETE_DISCLOSURE: '+key)
    for k in TEXT_FIELDS:filled(k)
    if value.get('run_kind') not in ('external','local_control'):raise ValueError('INVALID_DISCLOSURE: run_kind')
    if value.get('suite_version')!=__version__:raise ValueError('DISCLOSURE_VERSION_MISMATCH')
    for key in ('candidate_gold_access','candidate_positive_control_route_access'):
        if type(value.get(key)) is not bool:raise ValueError('INVALID_DISCLOSURE_BOOLEAN: '+key)
    # Reject placeholders recursively, including optional fields provided by the user.
    def walk(v):
        if isinstance(v,str) and 'AUTHOR_TO_COMPLETE' in v:raise ValueError('INCOMPLETE_DISCLOSURE')
        if isinstance(v,dict):
            for item in v.values():walk(item)
        if isinstance(v,list):
            for item in v:walk(item)
    walk(value)
    if value['run_kind']=='external':
        for k in EXTERNAL_TEXT:filled(k)
        filled('access_date_utc')
        try:dt=datetime.fromisoformat(value['access_date_utc'].replace('Z','+00:00'))
        except ValueError:raise ValueError('INVALID_DISCLOSURE_DATE') from None
        if dt.tzinfo is None:raise ValueError('INVALID_DISCLOSURE_DATE')
        for key in ('temperature','maximum_output_tokens'):
            if key not in value:raise ValueError('INCOMPLETE_DISCLOSURE: '+key)
            v=value[key]
            if v is None:filled(key+'_unavailable_reason')
            elif key=='temperature' and (type(v) not in (int,float) or not math.isfinite(v) or v<0):raise ValueError('INVALID_DISCLOSURE: '+key)
            elif key=='maximum_output_tokens' and (type(v) is not int or v<=0):raise ValueError('INVALID_DISCLOSURE: '+key)
    for key in ('input_task_sha256','catalog_sha256'):
        if key in value and (not isinstance(value[key],str) or re.fullmatch('[0-9a-f]{64}',value[key]) is None):raise ValueError('INVALID_DISCLOSURE_HASH: '+key)
    return value
