"""Verify current metadata and task accounting without rewriting historical evidence."""
from pathlib import Path
import sys,json,re,ast
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cardiobench import __version__
from cardiobench.core import ROOT,DATA,load_release,read_json,source_verify

def validate_current_docs(root):
    root=Path(root)
    expected={'README.md':'# NHANES-CardioBench '+__version__, 'docs/protocol.md':'# Protocol '+__version__}
    for name,heading in expected.items():
        text=(root/name).read_text(encoding='utf-8')
        if text.splitlines()[0]!=heading:raise ValueError('CURRENT_DOCUMENT_VERSION_MISMATCH: '+name)
    if 'Version '+__version__+' denotes this supplied candidate distribution.' not in (root/'docs/protocol.md').read_text(encoding='utf-8'):raise ValueError('CURRENT_PROTOCOL_VERSION_MISMATCH')
    if 'Version '+__version__+' has 89 canonical workloads' not in (root/'README.md').read_text(encoding='utf-8'):raise ValueError('CURRENT_README_VERSION_MISMATCH')
    for version in ('0_4_1','0_4_2','0_4_3','0_4_4','0_4_5','0_4_6','0_4_7'):
        name='docs/audit_resolution_v'+version+'.md'
        if not (root/name).is_file() or name not in (root/'README.md').read_text(encoding='utf-8'):raise ValueError('HISTORICAL_AUDIT_LINK_MISMATCH')

def check(require_artifacts=True):
    validate_current_docs(ROOT)
    result=source_verify(require_artifacts);tasks,gold,catalog=load_release();release=read_json(DATA/'release.json')
    from cardiobench.reproduction_evidence import validate_reproduction
    validate_reproduction(ROOT,ROOT/'results/paper',tasks,gold,catalog,allow_primary_staging=True)
    if release['version']!=__version__:raise ValueError('RELEASE_VERSION_MISMATCH')
    for name in ('pyproject.toml','CITATION.cff','codemeta.json','README.md'):
        if __version__ not in (ROOT/name).read_text(encoding='utf-8'):raise ValueError('VERSION_METADATA_MISMATCH: '+name)
    for field,actual in [('checks',len(tasks)),('canonical_workloads',len({t['canonical_id'] for t in tasks})),('development_checks',sum(t['split']=='development' for t in tasks)),('evaluation_checks',sum(t['split']=='evaluation' for t in tasks))]:
        if release[field]!=actual:raise ValueError('RELEASE_COUNT_MISMATCH: '+field)
    if '## Second revision 0.3.1' in (ROOT/'docs/protocol.md').read_text():raise ValueError('HISTORICAL_VERSION_MISLABELLED')
    total=sum(sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_') for n in ast.walk(ast.parse(p.read_text(encoding='utf-8')))) for p in (ROOT/'tests').glob('test_*.py'))
    log=(ROOT/'results/paper/unit_test_log.txt').read_text(encoding='utf-8')
    recorded=re.search(r'Ran (\d+) tests',log)
    if recorded is None or int(recorded.group(1))!=total or not log.rstrip().endswith('OK'):raise ValueError('TEST_COUNT_OR_STATUS_MISMATCH')
    from cardiobench.delivery_evidence import delivery_identity
    return {'evidence_binding':delivery_identity(ROOT),'test_methods':total,'status':'passed','version':__version__,**result}
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--core-only',action='store_true',help='Staging check only; does not certify a complete delivery');args=p.parse_args()
    try:result=check(not args.core_only)
    except (ValueError,OSError) as e:p.exit(2,str(e)+'\n')
    result['scope']='core staging gate' if args.core_only else 'complete delivery gate'
    print(json.dumps(result,indent=2))
