"""Trusted adapters, bounded capture and an authoritative resumable checkpoint."""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
import copy
import importlib.metadata
import base64, hashlib, json, math, os, platform, re, signal, subprocess, sys, threading, time, uuid
from . import __version__
from .core import DATA, parse_json, read_json, validate_response, summarize, ensure_finite
from .contracts import validate_task_response, CONTRACT_VERSION, response_descriptor
from .binding_contract import validate_binding, SAFE_ENV, positive_finite

def canonical(value):
    ensure_finite(value)
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def digest(value): return hashlib.sha256(canonical(value)).hexdigest()
def file_hash(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()

def atomic_json(path,value):
    from .io_safety import atomic_bytes
    atomic_bytes(path,canonical(value))

@contextmanager
def run_lock(dest):
    path=dest/'run.lock'
    try:fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise ValueError('RUN_LOCK_EXISTS: confirm no process is active before removing a stale run.lock')
    try:
        with os.fdopen(fd,'w') as out:json.dump({'pid':os.getpid(),'host':platform.node(),'created_utc':now()},out)
        yield
    finally:path.unlink(missing_ok=True)

def capture(adapter,payload,timeout,stdout_limit,stderr_limit,cwd=None,env=None):
    """Limit retained bytes while reading, not after communicate completes."""
    proc=subprocess.Popen([sys.executable,str(adapter)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=(os.name=='posix'),cwd=cwd,env=env)
    buffers={'stdout':bytearray(),'stderr':bytearray()};overflow=threading.Event()
    def read_stream(name,pipe,limit):
        try:
            while True:
                chunk=os.read(pipe.fileno(),4096)
                if not chunk:break
                room=limit-len(buffers[name]);buffers[name].extend(chunk[:max(0,room)])
                if len(chunk)>room:overflow.set();break
        finally:pipe.close()
    def write_input():
        try:proc.stdin.write(payload)
        except (BrokenPipeError,OSError):pass
        finally:
            try:proc.stdin.close()
            except OSError:pass
    threads=[threading.Thread(target=read_stream,args=(name,getattr(proc,name),limit),daemon=True) for name,limit in [('stdout',stdout_limit),('stderr',stderr_limit)]]
    threads.append(threading.Thread(target=write_input,daemon=True))
    for thread in threads:thread.start()
    start=time.monotonic();error=None;interrupted=False
    try:
        while proc.poll() is None or any(t.is_alive() for t in threads):
            if overflow.is_set():error='ADAPTER_OUTPUT_LIMIT';break
            if time.monotonic()-start>=timeout:error='ADAPTER_TIMEOUT';break
            overflow.wait(0.005)
    except BaseException:
        interrupted=True
        raise
    finally:
        # Also reap descendants holding inherited pipes on POSIX.
        if interrupted or error or proc.poll() is None:
            try:
                if os.name=='posix':os.killpg(proc.pid,signal.SIGKILL)
                else:proc.kill()
            except ProcessLookupError:pass
        proc.wait()
        for thread in threads:thread.join(timeout=0.2)
    if overflow.is_set():error='ADAPTER_OUTPUT_LIMIT'
    if error is None and proc.returncode!=0:error='ADAPTER_EXIT_'+str(proc.returncode)
    raw_out=bytes(buffers['stdout']);raw_err=bytes(buffers['stderr'])
    try:stdout=raw_out.decode('utf-8')
    except UnicodeDecodeError:
        stdout=raw_out.decode('utf-8',errors='replace')
        if error is None:error='ADAPTER_INVALID_UTF8'
    return {'stdout':stdout,'stderr':raw_err.decode('utf-8',errors='replace'),'error':error,'returncode':proc.returncode,
            'stdout_sha256':hashlib.sha256(raw_out).hexdigest(),'stderr_sha256':hashlib.sha256(raw_err).hexdigest(),
            'stdout_retained_bytes':len(raw_out),'stderr_retained_bytes':len(raw_err),
            'stdout_base64':base64.b64encode(raw_out).decode('ascii'),'stderr_base64':base64.b64encode(raw_err).decode('ascii')}

def disclosure(path,track):
    if path is None:return {'status':'not supplied; external model, cost and network activity are unknown'}
    from .contracts import validate_disclosure
    value=read_json(path)
    validate_disclosure(value,track)
    return value

def execution_config(args,adapter):
    cwd=Path(getattr(args,'adapter_cwd',None) or adapter.parent).resolve()
    if not cwd.is_dir():raise ValueError('INVALID_ADAPTER_CWD')
    dependencies={str(Path(p).resolve()):file_hash(p) for p in getattr(args,'dependency_file',[]) or []}
    packages={}
    for name in getattr(args,'dependency_package',[]) or []:
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:raise ValueError('DEPENDENCY_PACKAGE_NOT_INSTALLED: '+name)
    config_path=getattr(args,'environment_file',None)
    declared=read_json(config_path) if config_path else {}
    if not isinstance(declared,dict) or not set(declared)<=SAFE_ENV or any(not isinstance(v,str) or '\x00' in v for v in declared.values()):raise ValueError('INVALID_ENVIRONMENT_CONFIG')
    effective={k:declared.get(k,os.environ.get(k)) for k in sorted(SAFE_ENV)}
    return {'cwd':str(cwd),'dependency_files_sha256':dependencies,'dependency_package_versions':packages,'safe_environment':effective,
            'other_environment':'inherited but not recorded; credentials and undeclared inputs are outside the fingerprint'}

def binding(args,tasks,catalog,gold=None):
    adapter=Path(args.adapter).resolve()
    if not adapter.is_file():raise ValueError('Adapter path does not exist')
    prompt=Path(args.prompt_file).read_text(encoding='utf-8') if args.prompt_file else None
    code={p.name:file_hash(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    value={'schema_version':4,'contract_version':CONTRACT_VERSION,'response_task_types':{t['id']:response_descriptor(t) for t in tasks},'suite_version':__version__,'task_ids':[t['id'] for t in tasks],
            'tasks_sha256':digest(tasks),'catalog_sha256':digest(catalog),'gold_file_sha256':file_hash(DATA/'gold.json'),'scoring_gold_sha256':digest(gold if gold is not None else read_json(DATA/'gold.json')),'evidence_policy_sha256':file_hash(DATA/'evidence_policy.json'),
            'execution':execution_config(args,adapter),
            'adapter_path':str(adapter),'launch_command':[sys.executable,str(adapter)],'python_executable':sys.executable,'python_executable_resolved':str(Path(sys.executable).resolve()),'adapter_sha256':file_hash(adapter),'runner_source_sha256':code,
            'python':sys.version,'platform':platform.platform(),'track':args.track,
            'timeout_seconds':args.timeout,'stdout_limit_bytes':args.stdout_limit,'stderr_limit_bytes':args.stderr_limit,
            'prompt_text':prompt,'prompt_sha256':digest(prompt),
            'disclosure':disclosure(args.disclosure,args.track),
            'retry_policy':'failed cases remain terminal unless --retry-failed is explicitly used',
            'adapter_dependencies':'only explicitly declared files/packages and allowlisted environment are fingerprinted; disclose other inputs'}
    return validate_binding(value,tasks),adapter

def save_state(dest,state):
    atomic_json(dest/'checkpoint.json',{'state':state,'sha256':digest(state)})

def request_payload(task,catalog,identity):
    from .contracts import candidate_contract
    payload={'task':task,'response_contract':candidate_contract(task)}
    if identity['track']=='provided-context':payload['catalog']=catalog
    if identity['prompt_text'] is not None:payload['prompt']=identity['prompt_text']
    return payload

def validate_state(envelope,identity):
    def fail(message='INVALID_CHECKPOINT'):raise ValueError(message)
    if not isinstance(envelope,dict) or set(envelope)!={'state','sha256'}:fail()
    state=envelope['state']
    if digest(state)!=envelope['sha256']:fail('CHECKPOINT_HASH_MISMATCH')
    if not isinstance(state,dict) or set(state)!={'run_id','created_utc','updated_utc','binding','records'}:fail()
    validate_binding(identity);validate_binding(state['binding'])
    if digest(state['binding'])!=digest(identity):fail('RESUME_BINDING_MISMATCH')
    if not isinstance(state['run_id'],str):fail()
    try:uuid.UUID(state['run_id'])
    except (ValueError,AttributeError):fail()
    def timestamp(value):
        if not isinstance(value,str):fail()
        try:dt=datetime.fromisoformat(value)
        except ValueError:fail()
        if dt.tzinfo is None:fail()
        return dt
    created=timestamp(state['created_utc']);updated=timestamp(state['updated_utc'])
    if updated<created:fail()
    if not isinstance(state['records'],list):fail()
    ids=identity['task_ids'];seen=set()
    for row in state['records']:
        if not isinstance(row,dict) or set(row)!={'id','attempts'}:fail('INVALID_CHECKPOINT_RECORD')
        tid=row['id']
        if not isinstance(tid,str) or tid not in ids or tid in seen or not isinstance(row['attempts'],list) or not row['attempts']:fail('INVALID_CHECKPOINT_RECORD')
        seen.add(tid)
        for index,attempt in enumerate(row['attempts']):
            required={'started_utc','request_sha256','response','stdout','stderr','error','seconds'}
            optional={'returncode','stdout_sha256','stderr_sha256','stdout_retained_bytes','stderr_retained_bytes','stdout_base64','stderr_base64'}
            if not isinstance(attempt,dict) or not required<=set(attempt) or not set(attempt)<=required|optional:fail('INVALID_CHECKPOINT_ATTEMPT')
            stamp=timestamp(attempt['started_utc'])
            if not created<=stamp<=updated:fail('ATTEMPT_TIME_OUTSIDE_RUN')
            if type(attempt['seconds']) not in (int,float) or attempt['seconds']<0:fail('INVALID_CHECKPOINT_ATTEMPT')
            try:finite=math.isfinite(attempt['seconds'])
            except OverflowError:finite=False
            if not finite:fail('INVALID_CHECKPOINT_ATTEMPT')
            for key in ['stdout','stderr']:
                if not isinstance(attempt[key],str):fail('INVALID_CHECKPOINT_ATTEMPT')
            for key in ['request_sha256','stdout_sha256','stderr_sha256']:
                if key in attempt and (not isinstance(attempt[key],str) or re.fullmatch('[0-9a-f]{64}',attempt[key]) is None):fail('INVALID_CHECKPOINT_ATTEMPT')
            for key in ['stdout_retained_bytes','stderr_retained_bytes']:
                if key in attempt and (type(attempt[key]) is not int or attempt[key]<0):fail('INVALID_CHECKPOINT_ATTEMPT')
            if 'returncode' in attempt and type(attempt['returncode']) is not int:fail('INVALID_CHECKPOINT_ATTEMPT')
            captured='returncode' in attempt
            if captured:
                if not optional<=set(attempt):fail('INCOMPLETE_CAPTURE')
                for stream in ['stdout','stderr']:
                    try:raw=base64.b64decode(attempt[stream+'_base64'],validate=True)
                    except (ValueError,TypeError):fail('INVALID_CAPTURE_BYTES')
                    if len(raw)!=attempt[stream+'_retained_bytes'] or hashlib.sha256(raw).hexdigest()!=attempt[stream+'_sha256'] or raw.decode('utf-8',errors='replace')!=attempt[stream]:fail('CAPTURE_MISMATCH')
                    if len(raw)>identity[stream+'_limit_bytes']:fail('CAPTURE_LIMIT_MISMATCH')
                if attempt['error'] is None:
                    if attempt['returncode']!=0:fail('SUCCESS_EXIT_MISMATCH')
                    raw=base64.b64decode(attempt['stdout_base64'])
                    parsed=parse_json(raw.decode('utf-8'));validate_task_response(identity['response_task_types'][tid],parsed)
                    if canonical(parsed)!=canonical(attempt['response']):fail('RESPONSE_STDOUT_MISMATCH')
                else:
                    error=attempt['error']
                    if error=='ADAPTER_OUTPUT_LIMIT':
                        if not any(attempt[k+'_retained_bytes']==identity[k+'_limit_bytes'] for k in ['stdout','stderr']):fail('OUTPUT_LIMIT_EVIDENCE_MISMATCH')
                    elif error=='ADAPTER_TIMEOUT':
                        timeout=identity.get('timeout_seconds')
                        if type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0:fail('INVALID_CHECKPOINT_TIMEOUT')
                        tolerance=min(0.001,timeout*0.001)
                        if attempt['seconds']+tolerance<timeout:fail('TIMEOUT_DURATION_MISMATCH')
                    else:
                        expected=None
                        if attempt['returncode']!=0:expected='ADAPTER_EXIT_'+str(attempt['returncode'])
                        else:
                            try:text=base64.b64decode(attempt['stdout_base64']).decode('utf-8')
                            except UnicodeDecodeError:expected='ADAPTER_INVALID_UTF8'
                            else:
                                try:parsed=parse_json(text)
                                except (ValueError,TypeError,OverflowError,OSError,RecursionError) as exc:expected='ADAPTER_RESPONSE_ERROR: '+str(exc)
                                else:
                                    try:validate_task_response(identity['response_task_types'][tid],parsed)
                                    except (ValueError,TypeError,OverflowError) as exc:expected='ADAPTER_FORMAT_ERROR: '+str(exc)
                        if expected is None or error!=expected:fail('FAILURE_CAPTURE_MISMATCH')
            elif set(attempt)&optional or not isinstance(attempt['error'],str) or not attempt['error'].startswith('ADAPTER_LAUNCH_ERROR:') or attempt['stdout'] or attempt['stderr']:fail('INVALID_LAUNCH_FAILURE')
            if attempt['error'] is None:
                validate_task_response(identity['response_task_types'][tid],attempt['response'])
                if index!=len(row['attempts'])-1:fail('SUCCESS_CANNOT_BE_RETRIED')
            elif not isinstance(attempt['error'],str) or not attempt['error'].strip() or attempt['response'] is not None:fail('INVALID_CHECKPOINT_ATTEMPT')
    return state

def report_documents(state,tasks,gold):
    """Reconstruct every derived document from the authoritative checkpoint."""
    predictions={};traces=[]
    for row in state['records']:
        last=row['attempts'][-1]
        if last['error'] is None:predictions[row['id']]=last['response']
        traces.append({'id':row['id'],**last,'attempt_count':len(row['attempts'])})
    score=summarize(tasks,gold,predictions)
    errors={}
    for row in traces:
        if row['error'] is not None:errors[row['error']]=errors.get(row['error'],0)+1
    format_failed=sum(bool(x['error']) and x['error'].startswith(('ADAPTER_RESPONSE_ERROR','ADAPTER_FORMAT_ERROR','ADAPTER_INVALID_UTF8')) for x in traces)
    failed=sum(x['error'] is not None for x in traces)
    score['run']={'run_id':state['run_id'],'binding_sha256':digest(state['binding']),'completed_cases':len(state['records']),
                  'total_cases':len(tasks),'status':'complete' if len(state['records'])==len(tasks) else 'partial',
                  'failed_cases':failed,'execution_failed_cases':failed-format_failed,'format_failed_cases':format_failed,'incorrect_answer_cases':sum(x['schema_valid'] and not x['answer_correct'] for x in score['rows']),'evidence_mismatch_cases':sum(x['schema_valid'] and x['answer_correct'] and not x['evidence_correct'] for x in score['rows']),'error_counts':errors,
                  'total_attempts':sum(len(r['attempts']) for r in state['records'])}
    manifest={'run_id':state['run_id'],'created_utc':state['created_utc'],'updated_utc':state['updated_utc'],
                                      'binding':state['binding'],'binding_sha256':digest(state['binding']),'environment_monitoring':'adapter network, API calls and cost are not monitored'}
    return {'predictions.json':predictions,'traces.json':traces,'score.json':score,'run_manifest.json':manifest}

def reports(dest,state,tasks,gold):
    documents=report_documents(state,tasks,gold)
    for name,value in documents.items():atomic_json(dest/name,value)
    score=documents['score.json']
    return score

def run_adapter(args,tasks,gold,catalog):
    import math
    # Isolate the run from caller-side mutation of Python objects.
    args,tasks,gold,catalog=copy.deepcopy((args,tasks,gold,catalog))
    if not positive_finite(args.timeout):raise ValueError('Timeout must be positive and finite')
    if any(type(n) is not int or n<=0 for n in [args.stdout_limit,args.stderr_limit]):raise ValueError('Output limits must be positive integers')
    if args.max_cases is not None and (type(args.max_cases) is not int or args.max_cases<=0):raise ValueError('max-cases must be a positive integer')
    if args.track not in ('provided-context','closed-book'):raise ValueError('INVALID_TRACK')
    if not isinstance(tasks,list):raise ValueError('INVALID_TASK_SELECTION')
    ids=[]
    for task in tasks:
        if not isinstance(task,dict) or not isinstance(task.get('id'),str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}',task['id']) is None:raise ValueError('INVALID_TASK_ID')
        ids.append(task['id'])
    if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_TASK_ID')
    if not isinstance(gold,dict) or any(tid not in gold for tid in ids):raise ValueError('MISSING_SCORING_GOLD')
    from .contracts import validate_tasks
    validate_tasks(tasks,gold)
    if args.retry_failed and not args.resume:raise ValueError('retry-failed requires resume')
    if not tasks:raise ValueError('EMPTY_TASK_SELECTION')
    identity,adapter=binding(args,tasks,catalog,gold)
    declared=identity['disclosure']
    for field,actual in [('input_task_sha256',identity['tasks_sha256']),('catalog_sha256',identity['catalog_sha256'])]:
        if field in declared and declared[field]!=actual:raise ValueError('DISCLOSURE_BINDING_MISMATCH: '+field)
    if 'task_subset' in declared:
        splits={t['split'] for t in tasks}
        subset=next(iter(splits)) if len(splits)==1 else 'all'
        if declared['task_subset']!=subset:raise ValueError('DISCLOSURE_BINDING_MISMATCH: task_subset')
    if 'time_limit_seconds_per_case' in declared and declared['time_limit_seconds_per_case']!=args.timeout:raise ValueError('DISCLOSURE_BINDING_MISMATCH: timeout')
    from .io_safety import guard_directory
    inputs=[adapter,*[p for p in [args.prompt_file,args.disclosure,getattr(args,'environment_file',None)] if p],*(getattr(args,'dependency_file',[]) or [])]
    guard_directory(args.out,inputs)
    dest=Path(args.out);dest.mkdir(parents=True,exist_ok=True)
    with run_lock(dest):
        if args.resume:
            state=validate_state(read_json(dest/'checkpoint.json'),identity)
            by_id={t['id']:t for t in tasks}
            for row in state['records']:
                p=dest/'requests'/(row['id']+'.json')
                expected=digest(request_payload(by_id[row['id']],catalog,identity))
                if not p.is_file() or file_hash(p)!=expected or any(a['request_sha256']!=expected for a in row['attempts']):raise ValueError('REQUEST_ARCHIVE_MISMATCH: '+row['id'])
        else:
            if any(p.name!='run.lock' for p in dest.iterdir()):raise ValueError('OUTPUT_DIRECTORY_NOT_EMPTY: choose a new directory or --resume')
            state={'run_id':str(uuid.uuid4()),'created_utc':now(),'updated_utc':now(),'binding':identity,'records':[]}
            save_state(dest,state)
        # Derived reports can always be rebuilt from the authoritative checkpoint.
        reports(dest,state,tasks,gold)
        existing={r['id']:r for r in state['records']};performed=0
        for task in tasks:
            tid=task['id'];previous=existing.get(tid)
            if previous and (previous['attempts'][-1]['error'] is None or not args.retry_failed):continue
            if args.max_cases is not None and performed>=args.max_cases:break
            # Detect changes to the adapter or declared prompt/config before each call.
            current,_=binding(args,tasks,catalog,gold)
            if current!=identity:raise ValueError('RUN_BINDING_CHANGED')
            payload=request_payload(task,catalog,identity)
            raw=canonical(payload);request_path=dest/'requests'/(tid+'.json')
            atomic_json(request_path,payload)
            started=time.perf_counter()
            attempt={'started_utc':now(),'request_sha256':hashlib.sha256(raw).hexdigest(),'response':None,'stdout':'','stderr':'','error':None}
            try:
                env=os.environ.copy()
                for key,value in identity['execution']['safe_environment'].items():
                    if value is None:env.pop(key,None)
                    else:env[key]=value
                try:captured=capture(adapter,raw,args.timeout,args.stdout_limit,args.stderr_limit,cwd=identity['execution']['cwd'],env=env)
                except OSError as exc:
                    attempt['error']='ADAPTER_LAUNCH_ERROR: '+str(exc)
                    captured={}
                attempt.update(captured)
                if attempt['error'] is None:
                    value=parse_json(attempt['stdout'])
                    try:validate_task_response(task,value)
                    except (ValueError,TypeError,OverflowError) as exc:attempt['error']='ADAPTER_FORMAT_ERROR: '+str(exc)
                    else:attempt['response']=value
            except (ValueError,TypeError,OverflowError,OSError,RecursionError) as exc:
                attempt['error']='ADAPTER_RESPONSE_ERROR: '+str(exc)
            attempt['seconds']=time.perf_counter()-started
            # The last case needs the same post-execution check as every other case.
            current,_=binding(args,tasks,catalog,gold)
            if current!=identity:raise ValueError('RUN_BINDING_CHANGED_DURING_ATTEMPT: result not committed')
            if previous:previous['attempts'].append(attempt)
            else:
                previous={'id':tid,'attempts':[attempt]};state['records'].append(previous);existing[tid]=previous
            state['updated_utc']=now();save_state(dest,state)
            reports(dest,state,tasks,gold);performed+=1
        return reports(dest,state,tasks,gold)
