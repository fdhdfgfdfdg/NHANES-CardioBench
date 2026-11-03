"""Compare version-bound review submissions; identities remain self-reported."""
import csv,json,io,hashlib,threading
from pathlib import Path
from datetime import datetime
from . import __version__
from .core import load_release,parse_json,DATA,ROOT,source_verify
from .contracts import validate_task_response,candidate_contract,CONTRACT_VERSION
from .runner import atomic_json,digest,file_hash

REVIEW_FORMAT_VERSION='2'
MAX_FILE_BYTES=16*1024*1024
MAX_FIELD_CHARS=65536
MAX_RESPONSE_BYTES=65536
COLUMNS=['task_id','review_input_sha256','reviewer_id','reviewed_utc','proposed_response_json','evidence_rationale','policy_concern']
_CSV_LOCK=threading.RLock()

def review_identity(tasks,catalog):
    """Commit to the reviewed inputs and protocol, never to proposed/gold answers."""
    return {'review_format_version':REVIEW_FORMAT_VERSION,'suite_version':__version__,
      'contract_version':CONTRACT_VERSION,'core_manifest_sha256':file_hash(ROOT/'MANIFEST_SHA256.json'),
      'release_sha256':file_hash(DATA/'release.json'),'tasks_sha256':digest(tasks),
      'catalog_sha256':digest(catalog),'response_contracts_sha256':digest({t['id']:candidate_contract(t) for t in tasks})}

def _read_form(path,tasks,identity):
    with Path(path).open('rb') as stream:raw=stream.read(MAX_FILE_BYTES+1)
    if len(raw)>MAX_FILE_BYTES:raise ValueError('REVIEW_FILE_TOO_LARGE')
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError:raise ValueError('REVIEW_INVALID_UTF8') from None
    expected={t['id']:t for t in tasks};rows={};reviewers=set();binding=digest(identity)
    # csv.field_size_limit is process-global; restore it even on a malformed file.
    with _CSV_LOCK:
        previous=csv.field_size_limit(MAX_FIELD_CHARS)
        reader=csv.DictReader(io.StringIO(text,newline=''),strict=True)
        try:
            if len(reader.fieldnames or [])!=len(COLUMNS) or set(reader.fieldnames or [])!=set(COLUMNS):raise ValueError('REVIEW_COLUMNS_MISMATCH: version 2 bound forms required')
            for row in reader:
                if set(row)!=set(COLUMNS) or any(v is None for v in row.values()):raise ValueError('REVIEW_ROW_WIDTH_MISMATCH')
                tid=row['task_id']
                if tid not in expected or tid in rows:raise ValueError('REVIEW_TASK_ID_MISMATCH')
                if row['review_input_sha256']!=binding:raise ValueError('REVIEW_INPUT_BINDING_MISMATCH: '+tid)
                for key in ('reviewer_id','reviewed_utc','proposed_response_json','evidence_rationale'):
                    if not row[key].strip():raise ValueError('INCOMPLETE_REVIEW: '+tid+':'+key)
                if len(row['proposed_response_json'].encode('utf-8'))>MAX_RESPONSE_BYTES:raise ValueError('REVIEW_RESPONSE_TOO_LARGE: '+tid)
                try:dt=datetime.fromisoformat(row['reviewed_utc'].replace('Z','+00:00'))
                except ValueError:raise ValueError('INVALID_REVIEW_DATE') from None
                if dt.tzinfo is None:raise ValueError('INVALID_REVIEW_DATE')
                response=parse_json(row['proposed_response_json']);validate_task_response(expected[tid],response)
                reviewers.add(row['reviewer_id']);rows[tid]={**row,'response':response}
        except csv.Error as exc:
            raise ValueError('REVIEW_CSV_ERROR at physical line '+str(reader.line_num)+': '+str(exc)) from None
        finally:csv.field_size_limit(previous)
    if set(rows)!=set(expected) or len(reviewers)!=1:raise ValueError('INCOMPLETE_OR_MIXED_REVIEW')
    return rows,next(iter(reviewers)),hashlib.sha256(raw).hexdigest()

def read_form(path,tasks):
    source_verify();current,_,catalog=load_release()
    if digest(tasks)!=digest(current):raise ValueError('REVIEW_TASK_SELECTION_MISMATCH')
    rows,reviewer,_=_read_form(path,tasks,review_identity(tasks,catalog));return rows,reviewer

def compare(a,b,out):
    source_verify();tasks,_,catalog=load_release();identity=review_identity(tasks,catalog)
    left,aid,ah=_read_form(a,tasks,identity);right,bid,bh=_read_form(b,tasks,identity)
    if aid==bid:raise ValueError('REVIEWERS_MUST_DIFFER')
    fields=['status','answer','evidence','reason_code'];rows=[]
    for t in tasks:
        tid=t['id'];x=left[tid]['response'];y=right[tid]['response']
        match={k:(set(x[k])==set(y[k]) if k=='evidence' else type(x[k]) is type(y[k]) and digest(x[k])==digest(y[k])) for k in fields}
        rows.append({'task_id':tid,'agreement':match,'all_agree':all(match.values()),'adjudication_status':'pending','proposal_A':x,'proposal_B':y,'review_A':left[tid],'review_B':right[tid]})
    report={'version':__version__,'contract_version':CONTRACT_VERSION,'review_format_version':REVIEW_FORMAT_VERSION,
      'status':'submitted forms validated; identities and independence are self-reported, not authenticated; adjudication pending','reviewers':[aid,bid],
      'provenance':{'form_A_sha256':ah,'form_B_sha256':bh,'review_input_sha256':digest(identity),'review_input_identity':identity,
        'validation':'verified release and matching reviewer-committed input identities; task-family schema only; no comparison with gold values'},
      'checks':len(tasks),'agreement_counts':{k:sum(r['agreement'][k] for r in rows) for k in fields},'complete_agreement':sum(r['all_agree'] for r in rows),'rows':rows}
    from .io_safety import guard_output
    guard_output(out,[a,b]);atomic_json(out,report)
    return report

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--reviewer-a',required=True);p.add_argument('--reviewer-b',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try:r=compare(a.reviewer_a,a.reviewer_b,a.out)
    except (ValueError,OSError,TypeError,csv.Error) as e:p.exit(2,str(e)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='rows'}))
if __name__=='__main__':main()

ADJUDICATION_COLUMNS=['task_id','status','adjudicator_id','final_response_json','decision_rationale','reviewed_utc']
REVIEW_README="Review format 2: retain review_input_sha256 exactly as supplied. It binds the\nreviewed tasks, catalog, response contracts, suite version and core manifest.\nOld unbound forms are rejected; do not assign a new hash to an old submission.\nUTF-8 CSV limits: 16 MiB per file, 65536 characters per field, 65536 UTF-8\nbytes per proposed response. Strict CSV parsing rejects malformed quoting.\nIndependent review has NOT been performed. All decisions are blank or pending.\nCoordinator: distribute only reviewer_inputs.json, the frozen official snapshots,\nand one blank reviewer CSV to each reviewer. Do NOT distribute the expected-answer\nfile or the other reviewer's form before independent responses are committed.\nReview each response, evidence link, ambiguity and authored policy. Freeze both\nforms before comparison with expected_answers_after_review.json. Resolve differences\nin adjudication.csv with a named adjudicator, rationale and date. Keep unresolved\ncases pending. Record identity and expertise with consent; do not infer agreement\nfrom blank fields. These are preparation materials, not a blinding enforcement\nsystem, inter-rater statistic or completed human validation. The comparison CLI validates\ntask-family response shape without consulting gold values; it preserves hashes,\nreview dates, rationales and concerns. Matching proposals are not verified truth.\n"
