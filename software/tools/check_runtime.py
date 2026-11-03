"""Record actual local reproduction and five-to-complete resume evidence."""
from pathlib import Path
import argparse,json,subprocess,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cardiobench import __version__
from cardiobench.core import ROOT,read_json,source_verify,parse_json
from cardiobench.runner import atomic_json,file_hash
from cardiobench.io_safety import guard_directory,atomic_bytes
from cardiobench.delivery_evidence import delivery_identity
from cardiobench.process_evidence import FORMAT_VERSION,SCOPE

def check(out):
    verification=source_verify();identity=delivery_identity(ROOT);out=Path(out).resolve();guard_directory(out)
    if out.exists() and any(out.iterdir()):raise ValueError('RUNTIME_EVIDENCE_OUTPUT_NOT_EMPTY')
    out.mkdir(parents=True,exist_ok=True);run=out/'resume_run'
    def call(arguments):
        done=subprocess.run([sys.executable,'-m','cardiobench',*arguments],cwd=ROOT,text=True,capture_output=True,check=True,timeout=240)
        return parse_json(done.stdout)
    command=[sys.executable,'-m','cardiobench','reproduce','--out',str(out/'process_reproduction')]
    started=time.perf_counter();done=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,check=True,timeout=240);seconds=time.perf_counter()-started
    repro=parse_json(done.stdout)
    timing={'report_format_version':FORMAT_VERSION,'version':__version__,'evidence_binding':identity,'seconds':seconds,'command':command,
      'python_executable':sys.executable,'output_directory':str(out/'process_reproduction'),'returncode':done.returncode,'stdout':done.stdout,'stderr':done.stderr,
      'verification_scope':verification['artifact_verification']['status'],
      'scope':SCOPE,
      'result':repro,'paper_results_sha256':file_hash(out/'process_reproduction/paper_results.json')}
    args=['run-adapter','--adapter',str(ROOT/'examples/trusted_reference_adapter.py'),'--split','development','--out',str(run),'--disclosure',str(ROOT/'examples/reference_disclosure.json')]
    first=call([*args,'--max-cases','5']);atomic_bytes(out/'resume_first_checkpoint.json',(run/'checkpoint.json').read_bytes())
    second=call([*args,'--resume']);before=file_hash(run/'checkpoint.json');third=call([*args,'--resume']);after=file_hash(run/'checkpoint.json')
    score=read_json(run/'score.json');total=score['run']['total_cases']
    if score['overall']['joint_correct']!=total or score['run']['total_attempts']!=total or before!=after:raise ValueError('RUNTIME_RESUME_FAILED')
    if delivery_identity(ROOT)!=identity:raise ValueError('RUNTIME_EVIDENCE_INPUTS_CHANGED')
    resume={'version':__version__,'status':'passed','evidence_binding':identity,'first':first,'resumed':second,'completed_resume':third,
      'final_joint_correct':total,'final_attempts':total,'completed_checkpoint_unchanged':before==after,'checkpoint_sha256':after,
      'completed_resume_before_sha256':before,'first_checkpoint_sha256':file_hash(out/'resume_first_checkpoint.json'),
      'scope':'trusted authored positive control, not an external model experiment'}
    atomic_json(out/'process_timing.json',timing);atomic_json(out/'resume_validation.json',resume)
    return {'status':'passed','version':__version__,'process_seconds':seconds,'resume_cases':total}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    try:result=check(args.out)
    except (ValueError,OSError,subprocess.SubprocessError) as e:p.exit(2,str(e)+'\n')
    print(json.dumps(result))
