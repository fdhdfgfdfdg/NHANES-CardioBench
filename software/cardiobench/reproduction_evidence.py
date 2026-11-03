"""Reconcile all deterministic reproduction fields and measured timing summaries."""
from pathlib import Path
import statistics
from .binding_contract import positive_finite
from . import __version__
from .core import read_json,run_builtin,reference,lexical,lexical_context,summarize
from .runner import digest,file_hash

SCOPE='Local conformance and two lexical retrieval baselines; no generative model evaluation'
TIMING_SCOPE='In-process runner only; excludes source download, installation, JSON loading and rendering'
CONTEXT_PROTOCOL={'fields':['label','question','target'],'k1':1.2,'b':0.75,'tuning':'fixed before this comparison; no task-specific tuning','scope':'same 16 public semantic checks; exploratory, not held-out'}

def deterministic_report(root,tasks,gold,pred,lex,context):
    from .__main__ import mutations
    root=Path(root);sem=[t for t in tasks if t['kind']=='semantic']
    report=summarize(tasks,gold,pred);lr=summarize(sem,gold,lex);cr=summarize(sem,gold,context)
    return {'version':__version__,'scope':SCOPE,'release':read_json(root/'cardiobench/data/release.json'),
      'reference':report,'legacy_reference':summarize(tasks[:80],gold,{t['id']:pred[t['id']] for t in tasks[:80]}),
      'extension_reference':summarize(tasks[80:],gold,{t['id']:pred[t['id']] for t in tasks[80:]}),
      'lexical':lr,'context_lexical':cr,'context_lexical_protocol':CONTEXT_PROTOCOL,
      'lexical_traces':[{'id':t['id'],'request':t['request']['concept'],'expected':gold[t['id']]['answer']['variable'],'retrieved':lex[t['id']]['answer']['variable'],'correct':lr['rows'][i]['joint_correct']} for i,t in enumerate(sem)],
      'context_comparison':[{'id':t['id'],'label_correct':lr['rows'][i]['joint_correct'],'context_correct':cr['rows'][i]['joint_correct'],'label_variable':lex[t['id']]['answer']['variable'],'context_variable':context[t['id']]['answer']['variable']} for i,t in enumerate(sem)],
      'mutations':mutations(tasks,gold),
      'input_hashes':{n:file_hash(root/'cardiobench/data'/n) for n in ('tasks.json','gold.json','catalog.json','release.json','positive_control_routes.json','evidence_policy.json')},
      'runner_source_hashes':{p.name:file_hash(p) for p in sorted((root/'cardiobench').glob('*.py'))}}

def check_csv(report):
    return ('id,kind,split,joint_correct,answer_correct,evidence_correct\n'+'\n'.join(','.join(str(row[k]) for k in ('id','kind','split','joint_correct','answer_correct','evidence_correct')) for row in report['rows'])+'\n').encode('utf-8')

def validate_timing(timing):
    scalar=('reference_first_seconds','lexical_seconds','context_lexical_seconds','warm_reference_median_seconds','warm_reference_min_seconds','warm_reference_max_seconds')
    required=set(scalar)|{'warm_reference_repeats','warm_reference_raw_seconds','scope'}
    if not isinstance(timing,dict) or set(timing)!=required:raise ValueError('REPRODUCTION_TIMING_INVALID')
    raw=timing['warm_reference_raw_seconds']
    if not isinstance(raw,list) or len(raw)!=30 or any(not positive_finite(x) for x in raw) or any(not positive_finite(timing[k]) for k in scalar):raise ValueError('REPRODUCTION_TIMING_INVALID')
    if type(timing['warm_reference_repeats']) is not int or timing['warm_reference_repeats']!=len(raw) or timing['scope']!=TIMING_SCOPE:raise ValueError('REPRODUCTION_TIMING_INVALID')
    if any(timing[k]!=v for k,v in [('warm_reference_median_seconds',statistics.median(raw)),('warm_reference_min_seconds',min(raw)),('warm_reference_max_seconds',max(raw))]):raise ValueError('REPRODUCTION_TIMING_MISMATCH')

def validate_reproduction(root,folder,tasks,gold,catalog,*,allow_primary_staging=False):
    root,folder=Path(root),Path(folder);sem=[t for t in tasks if t['kind']=='semantic'];predictions=[]
    for name,selected,fn in [('reference_predictions.json',tasks,reference),('lexical_predictions.json',sem,lexical),('context_lexical_predictions.json',sem,lexical_context)]:
        value=read_json(folder/name);expected,_=run_builtin(selected,catalog,fn)
        if digest(value)!=digest(expected):raise ValueError('REPRODUCTION_PREDICTIONS_MISMATCH: '+name)
        predictions.append(value)
    expected=deterministic_report(root,tasks,gold,*predictions);paper=read_json(folder/'paper_results.json')
    if not isinstance(paper,dict) or set(paper)!=set(expected)|{'verification','timing','environment'}:raise ValueError('REPRODUCTION_REPORT_FIELDS_MISMATCH')
    for key,value in expected.items():
        if digest(paper[key])!=digest(value):raise ValueError('REPRODUCTION_REPORT_MISMATCH: '+key)
    if (folder/'check_results.csv').read_bytes()!=check_csv(expected['reference']):raise ValueError('REPRODUCTION_CSV_MISMATCH')
    from .verification_evidence import validate_verification
    validate_verification(root,paper['verification'],allow_primary_staging=allow_primary_staging)
    validate_timing(paper['timing'])
    # Environment strings are observations, not authenticated host attestations.
    env=paper['environment']
    if not isinstance(env,dict) or any(not isinstance(env.get(k),str) or not env[k].strip() for k in ('python','platform','implementation','cpu_description','dependencies','timer')) or type(env.get('logical_cpus')) is not int or env['logical_cpus']<=0 or type(env.get('external_model_calls')) is not int or env['external_model_calls']!=0 or env.get('network_used_during_runs') is not False:raise ValueError('REPRODUCTION_ENVIRONMENT_INVALID')
    return paper
