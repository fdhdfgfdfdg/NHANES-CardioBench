"""Create blank independent-review materials; never fabricate reviewer decisions."""
from pathlib import Path
import argparse,csv,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cardiobench.core import load_release,source_verify,DATA
from cardiobench.contracts import candidate_contract,CONTRACT_VERSION
from cardiobench.runner import file_hash,atomic_json
from cardiobench import __version__
from cardiobench.review import review_identity,COLUMNS,ADJUDICATION_COLUMNS,REVIEW_README
from cardiobench.runner import digest
from cardiobench.io_safety import guard_output

def prepare(out):
    source_verify();tasks,gold,catalog=load_release();out=Path(out)
    names=['reviewer_inputs.json','reviewer_A.csv','reviewer_B.csv','adjudication.csv','expected_answers_after_review.json','README.txt']
    for name in names:
        guard_output(out/name)
        if (out/name).exists():raise ValueError('REVIEW_OUTPUT_EXISTS')
    out.mkdir(parents=True,exist_ok=True)
    identity=review_identity(tasks,catalog);input_hash=digest(identity)
    atomic_json(out/'reviewer_inputs.json',{'review_input_identity':identity,'review_input_sha256':input_hash,'version':__version__,'contract_version':CONTRACT_VERSION,'tasks':tasks,'catalog':catalog,'response_contracts':{t['id']:candidate_contract(t) for t in tasks},'input_hashes':{name:file_hash(DATA/name) for name in ['tasks.json','catalog.json']}})
    for reviewer in ['A','B']:
        with (out/f'reviewer_{reviewer}.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(COLUMNS)
            writer.writerows([t['id'],input_hash,'','','','',''] for t in tasks)
    with (out/'adjudication.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(ADJUDICATION_COLUMNS)
        writer.writerows([t['id'],'pending','','','',''] for t in tasks)
    (out/'expected_answers_after_review.json').write_text(json.dumps(gold,indent=2),encoding='utf-8')
    (out/'README.txt').write_text(REVIEW_README,encoding='utf-8')
    return {'tasks':len(tasks),'reviewers_completed':0,'adjudications_completed':0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args();print(json.dumps(prepare(args.out)))
