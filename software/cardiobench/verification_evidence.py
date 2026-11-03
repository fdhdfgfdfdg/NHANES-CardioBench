"""Reconcile verification observations, including explicitly staged core snapshots."""
from pathlib import Path
import ast, hashlib, re
from . import __version__
from .core import read_json, parse_json

FORMAT_VERSION = 2
NOT_BUNDLED = {'status':'not bundled','scope':'core source/resources verified; outer delivery evidence is not installed'}
PRIMARY_OUTPUTS = frozenset('results/paper/'+n for n in (
    'paper_results.json','reference_predictions.json','lexical_predictions.json',
    'context_lexical_predictions.json','check_results.csv'))

def core_observations(root, snapshot_text=None):
    root=Path(root)
    text=(root/'MANIFEST_SHA256.json').read_bytes().decode('utf-8') if snapshot_text is None else snapshot_text
    manifest=parse_json(text)
    data=root.parent/'data' if root.name=='_release' else root/'cardiobench/data';tasks=read_json(data/'tasks.json');catalog=read_json(data/'catalog.json')
    dev={t['group_id'] for t in tasks if t['split']=='development'}
    evaluation={t['group_id'] for t in tasks if t['split']=='evaluation'}
    return {'verification_format_version':FORMAT_VERSION,'core_manifest_snapshot':text,
      'core_manifest_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
      'distribution_files_verified':len(manifest['files']),
      'parsed_metadata_verified':{'components':len({v['file'] for v in catalog['variables']}),
        'variable_occurrences':len(catalog['variables']),
        'section_hash_scheme':'sha256 of HTMLParser section text; whitespace collapsed, UTF-8; v1',
        'parsed_metadata_equal':True},
      'source_snapshots_verified':len(read_json(root/'sources/manifest.json')),
      'checks':len(tasks),'canonical_workloads':len({t['canonical_id'] for t in tasks}),
      'groups_disjoint':not bool(dev&evaluation)}

def artifact_observation(root, status):
    if status=='not bundled':return dict(NOT_BUNDLED)
    if status!='verified':raise ValueError('VERIFICATION_ARTIFACT_SCOPE_INVALID')
    from .artifacts import PROFILE,REQUIRED_FILES,inventory,validate_packages
    return {'status':'verified','files':len(inventory(root)),'core_manifest_bound':True,
      'profile':PROFILE,'packages':validate_packages(root),'required_files_verified':len(REQUIRED_FILES),
      'authentication':'checksums and report bindings detect inconsistency; no external signature or trust anchor'}

def validate_verification(root,value,*,allow_primary_staging=False):
    from .runner import digest
    root=Path(root)
    def require(ok):
        if not ok:raise ValueError('VERIFICATION_OBSERVATION_MISMATCH')
    require(isinstance(value,dict) and isinstance(value.get('core_manifest_snapshot'),str))
    snapshot=parse_json(value['core_manifest_snapshot']);current=read_json(root/'MANIFEST_SHA256.json')
    require(isinstance(snapshot,dict) and set(snapshot)=={'version','algorithm','files'} and
      snapshot['version']==__version__ and snapshot['algorithm']=='sha256' and isinstance(snapshot['files'],dict))
    require(set(snapshot['files'])==set(current['files']))
    for name,sha in snapshot['files'].items():
        require(isinstance(sha,str) and re.fullmatch('[0-9a-f]{64}',sha) is not None)
        if not allow_primary_staging or name not in PRIMARY_OUTPUTS:require(sha==current['files'][name])
    if not allow_primary_staging:require(value['core_manifest_snapshot']==(root/'MANIFEST_SHA256.json').read_bytes().decode('utf-8'))
    observed=value.get('artifact_verification');require(isinstance(observed,dict))
    # Primary paper results are generated before the outer delivery is frozen.
    if allow_primary_staging:require(observed.get('status')=='not bundled')
    expected={**core_observations(root,value['core_manifest_snapshot']),
      'artifact_verification':artifact_observation(root,observed.get('status'))}
    require(digest(value)==digest(expected))
    return value

def test_method_count(root):
    return sum(sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')
      for n in ast.walk(ast.parse(p.read_text(encoding='utf-8')))) for p in (Path(root)/'tests').glob('test_*.py'))

def validate_staging_gate(root,gate,identity):
    from .runner import digest
    expected={'evidence_binding':identity,'test_methods':test_method_count(root),'status':'passed',
      'version':__version__,'scope':'core staging gate',**core_observations(root),
      'artifact_verification':dict(NOT_BUNDLED)}
    if digest(gate)!=digest(expected):raise ValueError('RELEASE_GATE_EVIDENCE_MISMATCH')
