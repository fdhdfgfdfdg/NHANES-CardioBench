from pathlib import Path
import json, math, re, collections, hashlib, time, platform, sys
from decimal import Decimal
from fractions import Fraction
from . import __version__

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE/'_release' if (PACKAGE/'_release').is_dir() else PACKAGE.parent
DATA = Path(__file__).resolve().parent / 'data'
STATUSES = {'answer', 'abstain', 'reject'}

MAX_JSON_DEPTH = 128
MAX_RESPONSE_DEPTH = 32
MAX_INTEGER_DIGITS = 4096
INTEGER_LIMIT = 10**MAX_INTEGER_DIGITS

def require_integer_environment():
    getter=getattr(sys,'get_int_max_str_digits',None)
    limit=getter() if getter else 0
    if limit and limit<MAX_INTEGER_DIGITS:
        raise ValueError('INCOMPATIBLE_INTEGER_ENVIRONMENT: Python int_max_str_digits must be 0 or at least 4096; current='+str(limit))

def check_integer(value):
    if type(value) is int and not -INTEGER_LIMIT < value < INTEGER_LIMIT:
        raise ValueError('INTEGER_LIMIT_EXCEEDED')

def rational(value):
    check_integer(value)
    return Fraction(value) if type(value) is int else Fraction(str(value))

def ensure_finite(value, max_depth=MAX_JSON_DEPTH):
    """Bound JSON object depth without consuming the Python call stack."""
    require_integer_environment()
    stack=[(value,0)]
    while stack:
        item,depth=stack.pop()
        check_integer(item)
        if isinstance(item,float) and not math.isfinite(item):raise ValueError('NONFINITE_NUMBER')
        if isinstance(item,(dict,list,tuple)):
            depth+=1
            if depth>max_depth:raise ValueError('JSON_DEPTH_LIMIT_EXCEEDED')
            if isinstance(item,dict):
                if any(not isinstance(k,str) for k in item):raise ValueError('JSON_OBJECT_KEYS_MUST_BE_STRINGS')
                children=item.values()
            else:children=item
            stack.extend((child,depth) for child in children)

def parse_json(text):
    require_integer_environment()
    # Check container depth before invoking the recursive standard-library decoder.
    depth=0;quoted=False;escaped=False
    for char in text:
        if quoted:
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
        elif char=='"':quoted=True
        elif char in '[{':
            depth+=1
            if depth>MAX_JSON_DEPTH:raise ValueError('JSON_DEPTH_LIMIT_EXCEEDED')
        elif char in ']}':depth-=1
    def no_constant(value): raise ValueError('Nonfinite JSON constant: '+value)
    def no_duplicates(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise ValueError('Duplicate JSON key: '+k)
            d[k]=v
        return d
    def bounded_int(token):
        if len(token.lstrip('-'))>MAX_INTEGER_DIGITS:raise ValueError('INTEGER_LIMIT_EXCEEDED')
        try:return int(token)
        except ValueError:raise ValueError('INTEGER_LIMIT_EXCEEDED') from None
    value=json.loads(text,parse_constant=no_constant,parse_int=bounded_int,object_pairs_hook=no_duplicates)
    ensure_finite(value)
    json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8')
    return value

def read_json(path):
    return parse_json(Path(path).read_text(encoding='utf-8'))

def load_release():
    return read_json(DATA/'tasks.json'), read_json(DATA/'gold.json'), read_json(DATA/'catalog.json')

def response(status='answer',answer=None,evidence=None,reason=None):
    return {'status':status,'answer':answer or {},'evidence':evidence or [],'reason_code':reason}

def variable(catalog,file,code):
    return next((v for v in catalog['variables'] if v['file']==file and v['variable']==code),None)

def clean_code(value):
    """Shared cleaning input rule; ordinary text is retained, nonfinite codes fail."""
    if value is None:return None
    if type(value) not in (int,float,str):raise ValueError('INVALID_CODE_VALUE')
    check_integer(value)
    try: number=Decimal(value) if type(value) is int else Decimal(str(value))
    except __import__('decimal').InvalidOperation:return None
    if not number.is_finite():raise ValueError('INVALID_CODE_VALUE')
    return number if number==number.to_integral_value() else None

def validate_clean_values(values):
    if not isinstance(values,list):raise ValueError('INVALID_TASK_VALUES')
    for value in values:clean_code(value)
    return values

def clean_values(f,values):
    validate_clean_values(values)
    records=[row for row in f['values'] if row['meaning'].lower() in ('refused',"don't know",'missing')]
    missing={clean_code(row['code']) for row in records};missing.discard(None)
    literal_missing={str(row['code']) for row in records}
    return [None if x is None or clean_code(x) in missing or (isinstance(x,str) and x in literal_missing) else x for x in values]

def convert_glucose_values(values,factor,decimals):
    """Decimal-input rational conversion, ties-to-even rounding, one float cast."""
    if not isinstance(values,list) or any(type(x) not in (int,float) for x in values):
        raise ValueError('INVALID_TASK_VALUES')
    ensure_finite(values)
    if type(factor) not in (int,float) or (type(factor) is float and not math.isfinite(factor)) or type(decimals) is not int or not 0<=decimals<=18:
        raise ValueError('INVALID_CONVERSION_POLICY')
    multiplier=rational(factor);result=[]
    for value in values:
        rounded=round(rational(value)*multiplier,decimals)
        try:converted=float(rounded)
        except OverflowError:raise ValueError('NONFINITE_RESULT') from None
        if not math.isfinite(converted):raise ValueError('NONFINITE_RESULT')
        result.append(converted)
    return result

MAX_GRAPH_NODES=10000
MAX_GRAPH_EDGES=100000

def validate_graph(labels,features):
    def names(items):return isinstance(items,list) and all(isinstance(x,str) and x.strip() for x in items) and len(items)==len(set(items))
    if not names(labels) or not isinstance(features,dict):raise ValueError('INVALID_DEPENDENCY_GRAPH')
    if any(not isinstance(k,str) or not k.strip() or not names(v) for k,v in features.items()):raise ValueError('INVALID_DEPENDENCY_GRAPH')
    nodes=set(features)|set(labels);edges=0
    for deps in features.values():nodes.update(deps);edges+=len(deps)
    if len(nodes)>MAX_GRAPH_NODES or edges>MAX_GRAPH_EDGES:raise ValueError('GRAPH_LIMIT_EXCEEDED')
    return nodes

def trace_dependencies(labels,features):
    """Iterative DFS detects every cycle and propagates only label reachability."""
    validate_graph(labels,features)
    labels=set(labels);color={};depends={}
    for start in features:
        if color.get(start)==2:continue
        color[start]=1;stack=[(start,iter(features.get(start,[])))]
        while stack:
            node,children=stack[-1]
            try:child=next(children)
            except StopIteration:
                depends[node]=node in labels or any(depends[d] for d in features.get(node,[]))
                color[node]=2;stack.pop();continue
            if color.get(child)==1:raise ValueError('CYCLIC_DEPENDENCY')
            if color.get(child)!=2:
                color[child]=1;stack.append((child,iter(features.get(child,[]))))
    return sorted(name for name in features if depends[name])

def validate_fixture(r):
    if not isinstance(r, dict): raise ValueError('INVALID_FIXTURE')
    if r.get('synthetic') is not True: raise ValueError('FIXTURE_NOT_DECLARED_SYNTHETIC')
    fields=('key','weight_column','age_column','value_column')
    if any(k not in r for k in (*fields,'left','right','minimum_age')):
        raise ValueError('MISSING_FIELD')
    if any(not isinstance(r[k],str) or not r[k] for k in fields):
        raise ValueError('INVALID_COLUMN_NAME')
    key=r['key']; wc=r['weight_column']; ac=r['age_column']; vc=r['value_column']
    def number(x):
        check_integer(x)
        return type(x) in (int,float) and (not isinstance(x,float) or math.isfinite(x))
    if not number(r['minimum_age']) or r['minimum_age'] < 0: raise ValueError('INVALID_MINIMUM_AGE')
    for side in ('left','right'):
        if not isinstance(r[side],list) or any(not isinstance(row,dict) for row in r[side]):
            raise ValueError('INVALID_ROWS')
        ids=[]
        for row in r[side]:
            if key not in row: raise ValueError('MISSING_COLUMN')
            if type(row[key]) is not int or row[key] <= 0: raise ValueError('INVALID_KEY')
            check_integer(row[key])
            ids.append(row[key])
        if len(set(ids))!=len(ids): raise ValueError('DUPLICATE_KEY')
    for row in r['left']:
        if wc not in row or ac not in row: raise ValueError('MISSING_COLUMN')
        w=row[wc]
        if w is not None and (not number(w) or w<0): raise ValueError('INVALID_WEIGHT')
        if not number(row[ac]) or row[ac]<0: raise ValueError('INVALID_AGE')
    for row in r['right']:
        if vc not in row: raise ValueError('MISSING_COLUMN')
        if row[vc] is not None and not number(row[vc]): raise ValueError('INVALID_VALUE')
    return key,wc,ac,vc

def execute_fixture(r):
    key,wc,ac,vc=validate_fixture(r)
    right={row[key]:row for row in r['right']}
    selected=[]
    for row in r['left']:
        x=right.get(row[key],{}).get(vc); w=row[wc]
        if row[ac]>=r['minimum_age'] and x is not None and w is not None and w>0:
            selected.append((x,w))
    if not selected: raise ValueError('EMPTY_ANALYSIS')
    # Exact decimal-value rational accumulation; round only the final quotient.
    total=sum((rational(x)*rational(w) for x,w in selected),Fraction(0))
    weights=sum((rational(w) for _,w in selected),Fraction(0))
    try: mean=float(total/weights)
    except OverflowError: raise ValueError('NONFINITE_RESULT') from None
    if not math.isfinite(mean): raise ValueError('NONFINITE_RESULT')
    return {'joined_rows':len(r['left']),'cohort_n':len(selected),'weighted_mean':mean}

def reference(task,catalog):
    """Positive control, not a competitive model. Authored semantic routes are used."""
    r=task['request'];kind=task['kind']
    if task['cycle']!=catalog['cycle']:
        return response('abstain',evidence=['CORPUS:MANIFEST'],reason='CYCLE_OUT_OF_SCOPE')
    if kind=='semantic':
        routes=read_json(DATA/'positive_control_routes.json')
        route=next((x for x in routes if x['concept']==r['concept']),None)
        if route is None:return response('abstain',evidence=['CORPUS:MANIFEST'],reason='NOT_IN_RELEASE')
        return response(answer={'variable':route['variable'],'file':route['file']},evidence=[route['evidence_id']])
    if kind=='coding':
        op=r['operation']
        if op=='convert_glucose':
            c=catalog['conversion']
            try:values=convert_glucose_values(r['values'],c['factor'],c['decimals'])
            except ValueError as exc:
                if str(exc) not in ('NONFINITE_RESULT','INTEGER_LIMIT_EXCEEDED'):raise
                return response('reject',evidence=['GLU_J:CONVERSION'],reason=str(exc))
            return response(answer={'values':values},evidence=['GLU_J:CONVERSION'])
        f=variable(catalog,r['file'],r['variable'])
        if f is None:return response('abstain',evidence=['CORPUS:MANIFEST'],reason='NOT_IN_RELEASE')
        if op=='unit':
            u=catalog['units'].get(r['variable'])
            if u is None:return response('abstain',evidence=['CORPUS:MANIFEST'],reason='UNIT_NOT_CURATED')
            return response(answer={'unit':u},evidence=[f['evidence_id']])
        if op=='clean':return response(answer={'values':clean_values(f,r['values'])},evidence=[f['evidence_id']])
        raise ValueError('UNKNOWN_OPERATION')
    if kind=='weights':
        if r['analysis_cycle']!=catalog['cycle']:return response('abstain',evidence=['CORPUS:MANIFEST'],reason='CYCLE_OUT_OF_SCOPE')
        files=set(r['files'])
        if not files <= {v['file'] for v in catalog['variables']}:return response('abstain',evidence=['CORPUS:MANIFEST'],reason='NOT_IN_RELEASE')
        fasting=bool(files&{'GLU_J','TRIGLY_J'});diet='DR1TOT_J' in files
        if fasting and diet:return response('abstain',evidence=['POLICY:JOINT_WEIGHT'],reason='JOINT_WEIGHT_NOT_SPECIFIED')
        if fasting:
            w='WTSAF2YR';src='GLU_J' if 'GLU_J' in files else 'TRIGLY_J'
        elif diet:w='WTDRD1';src='DR1TOT_J'
        elif files&{'BPX_J','BMX_J','GHB_J','TCHOL_J','HDL_J'}:w='WTMEC2YR';src='DEMO_J'
        else:w='WTINT2YR';src='DEMO_J'
        return response(answer={'weight':w,'stratum':'SDMVSTRA','psu':'SDMVPSU'},evidence=[src+':'+w,'WEIGHTING:SELECTION'])
    if kind=='leakage':
        try:
            ex=trace_dependencies(r['label_sources'],r['feature_dependencies'])
            return response(answer={'excluded_features':ex},evidence=['POLICY:DEPENDENCY'])
        except ValueError as e:return response('reject',evidence=['POLICY:DEPENDENCY'],reason=str(e))
    if kind=='execution':
        try:return response(answer=execute_fixture(r),evidence=['POLICY:EXECUTION'])
        except ValueError as e:return response('reject',evidence=['POLICY:EXECUTION'],reason=str(e))
    raise ValueError('UNKNOWN_KIND')

STOP={'the','a','an','of','for','and','in','at','ever','you','had','have','told','doctor','reported','history','current','first','day','problem','professional','prescribed'}
def tokens(text):return [t for t in re.findall(r'[a-z0-9]+',text.lower()) if t not in STOP]

def lexical(task,catalog,fields=('label',)):
    """A disclosed BM25 label-only retrieval baseline for semantic tasks."""
    if task['kind']!='semantic':raise ValueError('LEXICAL_ONLY_SUPPORTS_SEMANTIC')
    variables=catalog['variables']; docs=[tokens(' '.join(v.get(field,'') for field in fields)) for v in variables];q=tokens(task['request']['concept'])
    N=len(docs);avg=sum(map(len,docs))/N
    df=collections.Counter(w for d in docs for w in set(d))
    scores=[]
    for i,d in enumerate(docs):
        tf=collections.Counter(d);score=0.0
        for w in q:
            f=tf[w]
            if f:
                idf=math.log(1+(N-df[w]+0.5)/(df[w]+0.5))
                score += idf*f*2.2/(f+1.2*(1-0.75+0.75*len(d)/avg))
        scores.append((score,-i))
    best=max(scores);v=variables[-best[1]]
    return response(answer={'variable':v['variable'],'file':v['file']},evidence=[v['evidence_id']])

def validate_response(r):
    if not isinstance(r,dict) or set(r)!={'status','answer','evidence','reason_code'}:raise ValueError('Response requires exactly status, answer, evidence and reason_code')
    if not isinstance(r['status'],str) or r['status'] not in STATUSES:raise ValueError('Invalid response status')
    if not isinstance(r['answer'],dict):raise ValueError('answer must be an object')
    if not isinstance(r['evidence'],list) or any(not isinstance(x,str) for x in r['evidence']):raise ValueError('evidence must be a string array')
    if len(r['evidence'])!=len(set(r['evidence'])):raise ValueError('Duplicate evidence identifier')
    if r['reason_code'] is not None and not isinstance(r['reason_code'],str):raise ValueError('reason_code must be null or string')
    if r['status']=='answer' and r['reason_code'] is not None:raise ValueError('An answer must have a null reason_code')
    if r['status']!='answer' and r['reason_code'] is None:raise ValueError('Abstention/rejection requires a reason_code')
    if isinstance(r['reason_code'],str) and not r['reason_code'].strip():raise ValueError('reason_code must not be empty')
    if r['status']!='answer' and r['answer']: raise ValueError('Non-answer requires an empty answer object')
    from .contracts import REASONS
    if r['reason_code'] is not None and r['reason_code'] not in REASONS:raise ValueError('UNKNOWN_REASON_CODE')
    if any(not x.strip() for x in r['evidence']):raise ValueError('EMPTY_EVIDENCE_IDENTIFIER')
    ensure_finite(r,MAX_RESPONSE_DEPTH)
    json.dumps(r,ensure_ascii=False,allow_nan=False).encode('utf-8')

def validate_answer(r, expected, task):
    from .contracts import validate_task_response
    if task is None:raise ValueError('TASK_REQUIRED_FOR_ANSWER_SCHEMA')
    validate_task_response(task,r)

def equal(a,b):
    if isinstance(b,bool):return type(a) is bool and a==b
    if type(b) is int: return type(a) is int and a==b
    if isinstance(b,float):
        try:
            return not isinstance(a,bool) and isinstance(a,(int,float)) and math.isfinite(a) and math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-10)
        except OverflowError:
            return False
    if isinstance(b,dict):return isinstance(a,dict) and set(a)==set(b) and all(equal(a[k],b[k]) for k in b)
    if isinstance(b,list):return isinstance(a,list) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return type(a) is type(b) and a==b

def grade(actual,expected,task):
    if task is None:raise ValueError('TASK_REQUIRED_FOR_ANSWER_SCHEMA')
    try:
        validate_response(actual)
        validate_answer(actual,expected,task)
    except (ValueError,TypeError,OverflowError) as e:return {'schema_valid':False,'answer_correct':False,'evidence_correct':False,'joint_correct':False,'error':str(e)}
    ans=actual['status']==expected['status'] and actual['reason_code']==expected['reason_code'] and equal(actual['answer'],expected['answer'])
    ev=set(actual['evidence'])==set(expected['evidence'])
    return {'schema_valid':True,'answer_correct':ans,'evidence_correct':ev,'joint_correct':ans and ev,'error':None if ans and ev else ('ANSWER_MISMATCH' if not ans else 'EVIDENCE_MISMATCH')}

def summarize(tasks,gold,predictions):
    from .contracts import validate_tasks
    validate_tasks(tasks,gold)
    if not isinstance(predictions,dict): raise ValueError('INVALID_PREDICTIONS')
    ids={t['id'] for t in tasks}
    if not set(predictions)<=ids:raise ValueError('Unknown or out-of-scope response IDs: '+','.join(sorted(set(predictions)-ids)))
    rows=[]
    for t in tasks:
        g=grade(predictions[t['id']],gold[t['id']],t) if t['id'] in predictions else {'schema_valid':False,'answer_correct':False,'evidence_correct':False,'joint_correct':False,'error':'MISSING_RESPONSE'}
        rows.append({'id':t['id'],'canonical_id':t['canonical_id'],'kind':t['kind'],'group_id':t['group_id'],'split':t['split'],**g})
    def counts(rs):
        return {'checks':len(rs),'joint_correct':sum(x['joint_correct'] for x in rs),'answer_correct':sum(x['answer_correct'] for x in rs),'evidence_correct':sum(x['evidence_correct'] for x in rs),'schema_valid':sum(x['schema_valid'] for x in rs)}
    strict = {'version':__version__,'overall':counts(rows),'families':{k:counts([x for x in rows if x['kind']==k]) for k in sorted({x['kind'] for x in rows})},'splits':{s:counts([x for x in rows if x['split']==s]) for s in sorted({x['split'] for x in rows})},'rows':rows}
    policy=read_json(DATA/'evidence_policy.json')
    from .contracts import task_fingerprint
    task_by_id={task['id']:task for task in tasks}
    adjusted=[]
    for row in rows:
        pred=predictions.get(row['id'])
        bound=(policy.get('version')==__version__ and policy.get('task_fingerprints',{}).get(row['id'])==task_fingerprint(task_by_id[row['id']]) and policy.get('gold_fingerprints',{}).get(row['id'])==task_fingerprint(gold[row['id']]))
        alt=policy['alternatives'].get(row['id'],[]) if bound else []
        evidence_ok=row['evidence_correct'] or (row['schema_valid'] and any(set(pred['evidence'])==set(x) for x in alt))
        joint=row['answer_correct'] and bool(evidence_ok)
        error=None if joint else (row['error'] if not row['schema_valid'] else ('ANSWER_MISMATCH' if not row['answer_correct'] else 'EVIDENCE_MISMATCH'))
        adjusted.append({**row,'evidence_correct':bool(evidence_ok),'joint_correct':joint,'error':error,'primary_error':row['error'],'alternative_policy_applicable':bound})
    strict['policy_adjusted']={'policy_version':policy['version'],'status':policy['review_status'],'overall':counts(adjusted),'rows':adjusted}
    return strict

def distribution_verify(root=None):
    """Verify the requested source or installed-resource root, never another tree."""
    root=ROOT if root is None else Path(root).resolve()
    package=root.parent if root.name=='_release' else root/'cardiobench'
    manifest=read_json(root/'MANIFEST_SHA256.json')
    if not isinstance(manifest,dict) or manifest.get('version')!=__version__ or manifest.get('algorithm')!='sha256' or not isinstance(manifest.get('files'),dict):raise ValueError('INVALID_CORE_MANIFEST')
    files=manifest['files']
    required={p.relative_to(root).as_posix() for directory in ('cardiobench','sources','tests','tools','docs')
              for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    if root.name=='_release':
        required |= {'cardiobench/'+p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file() and '_release' not in p.relative_to(package).parts and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    required |= {'README.md','LICENSE','CITATION.cff','codemeta.json','requirements.txt','requirements-build.txt','environment.lock.json','.python-version','.github/workflows/check.yml','pyproject.toml','setup.py','MANIFEST.in','.gitattributes'}
    if not required <= set(files): raise ValueError('MANIFEST_COVERAGE_MISSING')
    for name,digest in files.items():
        path=(package.parent/name) if root.name=='_release' and name.startswith('cardiobench/') else root/name
        if Path(name).is_absolute() or '..' in Path(name).parts: raise ValueError('INVALID_MANIFEST_PATH')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('DISTRIBUTION_HASH_MISMATCH: '+name)
    return len(files)

def source_verify(require_artifacts=False):
    verified_files=distribution_verify()
    from .artifacts import verify_artifacts
    artifacts=verify_artifacts(ROOT,require=require_artifacts)
    manifest=read_json(ROOT/'sources'/'manifest.json')
    for item in manifest:
        p=ROOT/item['path']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('SOURCE_HASH_MISMATCH: '+item['id'])
    from .sources import verify_parsed
    parsed_verification=verify_parsed(ROOT)
    tasks,gold,catalog=load_release()
    from .contracts import validate_tasks
    validate_tasks(tasks,gold)
    if len({t['id'] for t in tasks})!=len(tasks) or set(gold)!={t['id'] for t in tasks}:raise ValueError('Task/gold identity mismatch')
    dev={t['group_id'] for t in tasks if t['split']=='development'};ev={t['group_id'] for t in tasks if t['split']=='evaluation'}
    if dev&ev:raise ValueError('Group crosses subsets')
    known={v['evidence_id'] for v in catalog['variables']}|set(catalog['policy_evidence'])
    for tid,g in gold.items():
        validate_response(g)
        if not set(g['evidence'])<=known:raise ValueError('Unresolved evidence in '+tid)
    from .verification_evidence import core_observations
    return {**core_observations(ROOT),'artifact_verification':artifacts}

def environment():
    return {'python':sys.version,'platform':platform.platform(),'implementation':platform.python_implementation(),'logical_cpus':__import__('os').cpu_count(),'cpu_description':next((x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),'not recorded') if Path('/proc/cpuinfo').exists() else 'not recorded','dependencies':'Python standard library only','external_model_calls':0,'network_used_during_runs':False,'timer':'time.perf_counter; end-to-end process latency recorded separately'}

def run_builtin(tasks,catalog,fn):
    before=time.perf_counter();out={t['id']:fn(t,catalog) for t in tasks}
    return out,time.perf_counter()-before

def lexical_context(task,catalog):
    """Fixed BM25 over label, question and target; no gold or task-specific tuning."""
    return lexical(task,catalog,fields=('label','question','target'))
