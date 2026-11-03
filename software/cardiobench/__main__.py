"""Offline commands; candidate predictions are never evaluated as Python code."""
from pathlib import Path
import argparse, json, time, copy, statistics, hashlib, subprocess, sys
from .core import *
from . import __version__

def dump(path,obj):
    from .runner import atomic_json
    atomic_json(path,obj)

def select(tasks,split='all',kind='all'):
    return [t for t in tasks if (split=='all' or t['split']==split) and (kind=='all' or t['kind']==kind)]

def record_inputs():
    return {name:hashlib.sha256((DATA/name).read_bytes()).hexdigest() for name in ['tasks.json','gold.json','catalog.json','release.json','positive_control_routes.json','evidence_policy.json']}

def mutations(tasks,gold):
    results=[]
    for t in tasks:
        original=gold[t['id']]
        for kind in ['content','evidence','status']:
            r=copy.deepcopy(original)
            if kind=='evidence':r['evidence']=[]
            elif kind=='status':
                if r['status']=='answer':r=response('abstain',evidence=r['evidence'],reason='NOT_IN_RELEASE')
                else:r=response('reject' if r['status']=='abstain' else 'abstain',evidence=r['evidence'],reason=r['reason_code'])
            elif r['status']!='answer':
                from .contracts import REASONS
                r['reason_code']=next(code for code in REASONS if code!=r['reason_code'])
            else:
                first=next(iter(r['answer']))
                v=r['answer'][first]
                if isinstance(v,str):r['answer'][first]=v+'_WRONG'
                elif isinstance(v,(int,float)):r['answer'][first]=v+1
                elif isinstance(v,list):r['answer'][first]=v[:-1] if v else ['INVENTED']
                else:r['answer'][first]={'wrong':1}
            g=grade(r,original,t)
            results.append({'id':t['id'],'mutation':kind,'schema_valid':g['schema_valid'],'detected':not g['joint_correct']})
    return {'mutation_protocol_version':'1.1','schema_valid_records':sum(x['schema_valid'] for x in results),'historical_comparability':'34 non-answer perturbations changed from v0.4.0 to obey contract 1.1; compare protocols explicitly.','perturbed_records':len(results),'detected':sum(x['detected'] for x in results),'all_detected':all(x['detected'] for x in results),'rows':results}

def reproduce(out):
    from .io_safety import guard_output
    out=Path(out)
    for name in ['paper_results.json','reference_predictions.json','lexical_predictions.json','context_lexical_predictions.json','check_results.csv']:guard_output(out/name)
    tasks,gold,catalog=load_release();verify=source_verify()
    out.mkdir(parents=True,exist_ok=True)
    preds,seconds=run_builtin(tasks,catalog,reference)
    report=summarize(tasks,gold,preds)
    sem=[t for t in tasks if t['kind']=='semantic']
    lex,lexseconds=run_builtin(sem,catalog,lexical)
    lr=summarize(sem,gold,lex)
    context,contextseconds=run_builtin(sem,catalog,lexical_context)
    context_report=summarize(sem,gold,context)
    traces=[{'id':t['id'],'request':t['request']['concept'],'expected':gold[t['id']]['answer']['variable'],'retrieved':lex[t['id']]['answer']['variable'],'correct':lr['rows'][i]['joint_correct']} for i,t in enumerate(sem)]
    times=[]
    for _ in range(30):
        _,s=run_builtin(tasks,catalog,reference);times.append(s)
    mut=mutations(tasks,gold)
    results={'version':__version__,'scope':'Local conformance and two lexical retrieval baselines; no generative model evaluation','release':read_json(DATA/'release.json'),'verification':verify,'reference':report,'legacy_reference':summarize(tasks[:80],gold,{t['id']:preds[t['id']] for t in tasks[:80]}),'extension_reference':summarize(tasks[80:],gold,{t['id']:preds[t['id']] for t in tasks[80:]}),'lexical':lr,'lexical_traces':traces,'context_lexical':context_report,'context_lexical_protocol':{'fields':['label','question','target'],'k1':1.2,'b':0.75,'tuning':'fixed before this comparison; no task-specific tuning','scope':'same 16 public semantic checks; exploratory, not held-out'},'context_comparison':[{'id':t['id'],'label_correct':lr['rows'][i]['joint_correct'],'context_correct':context_report['rows'][i]['joint_correct'],'label_variable':lex[t['id']]['answer']['variable'],'context_variable':context[t['id']]['answer']['variable']} for i,t in enumerate(sem)],'mutations':mut,'timing':{'reference_first_seconds':seconds,'lexical_seconds':lexseconds,'context_lexical_seconds':contextseconds,'warm_reference_repeats':30,'warm_reference_median_seconds':statistics.median(times),'warm_reference_min_seconds':min(times),'warm_reference_max_seconds':max(times),'warm_reference_raw_seconds':times,'scope':'In-process runner only; excludes source download, installation, JSON loading and rendering'},'environment':environment(),'input_hashes':record_inputs(),'runner_source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))}}
    dump(out/'paper_results.json',results)
    dump(out/'reference_predictions.json',preds)
    dump(out/'lexical_predictions.json',lex)
    dump(out/'context_lexical_predictions.json',context)
    from .io_safety import atomic_bytes
    csv_text=('id,kind,split,joint_correct,answer_correct,evidence_correct\n'+'\n'.join(','.join(str(row[k]) for k in ['id','kind','split','joint_correct','answer_correct','evidence_correct']) for row in report['rows'])+'\n')
    atomic_bytes(out/'check_results.csv',csv_text.encode('utf-8'))
    print(json.dumps({'reference':report['overall'],'lexical_semantic':lr['overall'],'mutations':{k:v for k,v in mut.items() if k!='rows'},'out':str(out)},indent=2))

def main():
    p=argparse.ArgumentParser(prog='python -m cardiobench')
    subs=p.add_subparsers(dest='command',required=True)
    v=subs.add_parser('verify');v.add_argument('--require-artifacts',action='store_true')
    r=subs.add_parser('reproduce');r.add_argument('--out',default='results/reproduced')
    e=subs.add_parser('export');e.add_argument('--out',required=True);e.add_argument('--split',choices=['all','development','evaluation'],default='all');e.add_argument('--kind',choices=['all','semantic','coding','weights','leakage','execution'],default='all');e.add_argument('--track',choices=['provided-context','closed-book'],default='provided-context')
    s=subs.add_parser('score');s.add_argument('--responses',required=True);s.add_argument('--out',required=True);s.add_argument('--split',choices=['all','development','evaluation'],default='all');s.add_argument('--kind',choices=['all','semantic','coding','weights','leakage','execution'],default='all')
    a=subs.add_parser('run-adapter');a.add_argument('--adapter',required=True,help='Path to a trusted Python adapter accepting one JSON object on stdin');a.add_argument('--out',required=True);a.add_argument('--timeout',type=float,default=30);a.add_argument('--split',choices=['all','development','evaluation'],default='evaluation')
    a.add_argument('--track',choices=['provided-context','closed-book'],default='provided-context')
    a.add_argument('--resume',action='store_true')
    a.add_argument('--retry-failed',action='store_true')
    a.add_argument('--max-cases',type=int)
    a.add_argument('--prompt-file')
    a.add_argument('--disclosure')
    a.add_argument('--stdout-limit',type=int,default=1000000)
    a.add_argument('--stderr-limit',type=int,default=64000)
    a.add_argument('--adapter-cwd')
    a.add_argument('--dependency-file',action='append',default=[])
    a.add_argument('--dependency-package',action='append',default=[])
    a.add_argument('--environment-file')
    args=p.parse_args()
    try:
        if args.command=='verify':print(json.dumps(source_verify(args.require_artifacts),indent=2));return
        if args.command=='reproduce':reproduce(args.out);return
        source_verify()
        tasks,gold,catalog=load_release();tasks=select(tasks,args.split,getattr(args,'kind','all'))
        if not tasks:raise ValueError('EMPTY_TASK_SELECTION')
        if args.command=='export':
            from .contracts import candidate_contract
            export={'response_contracts':{t['id']:candidate_contract(t) for t in tasks},'version':__version__,'track':args.track,'tasks':tasks,'response_schema':{'status':'answer|abstain|reject','answer':'object','evidence':'unique evidence IDs','reason_code':'null for answers, string otherwise'},'disclosure_template':read_json(ROOT/'docs'/'run_disclosure_template.json')}
            export['input_hashes']={name:hashlib.sha256((DATA/name).read_bytes()).hexdigest() for name in ['tasks.json','catalog.json','release.json']}
            if args.track=='provided-context':export['catalog']=catalog
            dump(args.out,export)
        elif args.command=='score':
            from .io_safety import guard_output
            guard_output(args.out,[args.responses])
            response_bytes=Path(args.responses).read_bytes()
            predictions=parse_json(response_bytes.decode('utf-8'))
            if not isinstance(predictions,dict):raise ValueError('Predictions must be an object indexed by task ID')
            report=summarize(tasks,gold,predictions)
            report['provenance']={'input_hashes':record_inputs(),'responses_sha256':hashlib.sha256(response_bytes).hexdigest(),'split':args.split,'kind':args.kind,'runner_source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))}}
            dump(args.out,report)
        else:
            from .runner import run_adapter
            report=run_adapter(args,tasks,gold,catalog)
            print(json.dumps(report['run'],indent=2))
    except (ValueError,KeyError,OSError,TypeError,RecursionError,OverflowError) as exc:p.exit(2,'cardiobench: '+str(exc)+'\n')

if __name__=='__main__':main()
