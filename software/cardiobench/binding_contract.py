"""Validate live and archived run bindings without accessing archived host paths."""
from pathlib import PurePosixPath, PureWindowsPath
import math, re
from . import __version__
from .contracts import CONTRACT_VERSION, KINDS, validate_task_ids, validate_disclosure, response_descriptor
from .core import ensure_finite

SAFE_ENV = frozenset({'OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PYTHONHASHSEED','LANG','LC_ALL','TZ'})
UNKNOWN_DISCLOSURE = {'status':'not supplied; external model, cost and network activity are unknown'}
RETRY_POLICY = 'failed cases remain terminal unless --retry-failed is explicitly used'
DEPENDENCY_SCOPE = 'only explicitly declared files/packages and allowlisted environment are fingerprinted; disclose other inputs'
ENVIRONMENT_SCOPE = 'inherited but not recorded; credentials and undeclared inputs are outside the fingerprint'
FIELDS = frozenset(('schema_version contract_version response_task_types suite_version task_ids tasks_sha256 '
 'catalog_sha256 gold_file_sha256 scoring_gold_sha256 evidence_policy_sha256 execution adapter_path '
 'launch_command python_executable python_executable_resolved adapter_sha256 runner_source_sha256 python '
 'platform track timeout_seconds stdout_limit_bytes stderr_limit_bytes prompt_text prompt_sha256 disclosure '
 'retry_policy adapter_dependencies').split())

def require(ok, code='INVALID_RUN_BINDING'):
    if not ok: raise ValueError(code)

def nonempty(value):
    return isinstance(value,str) and bool(value.strip()) and '\x00' not in value

def absolute_path(value):
    return nonempty(value) and (PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute())

def sha256(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None

def positive_finite(value):
    if type(value) not in (int,float) or value<=0:return False
    try:return math.isfinite(value)
    except OverflowError:return False

def validate_binding(value, tasks=None):
    from .runner import digest
    ensure_finite(value)
    require(isinstance(value,dict) and set(value)==FIELDS)
    require(type(value['schema_version']) is int and value['schema_version']==4 and
      value['suite_version']==__version__ and value['contract_version']==CONTRACT_VERSION)
    require(positive_finite(value['timeout_seconds']),'INVALID_BINDING_TIMEOUT')
    require(all(type(value[k]) is int and value[k]>0 for k in ('stdout_limit_bytes','stderr_limit_bytes')),'INVALID_BINDING_OUTPUT_LIMIT')
    require(value['track'] in ('provided-context','closed-book'),'INVALID_BINDING_TRACK')
    ids=value['task_ids'];require(isinstance(ids,list) and bool(ids))
    validate_task_ids([{'id':tid} for tid in ids])
    descriptors=value['response_task_types'];require(isinstance(descriptors,dict) and set(descriptors)==set(ids))
    for descriptor in descriptors.values():
        require(isinstance(descriptor,dict) and set(descriptor)=={'kind','request'} and
          isinstance(descriptor['kind'],str) and descriptor['kind'] in KINDS and
          isinstance(descriptor['request'],dict) and set(descriptor['request'])=={'operation'})
        try:response_descriptor(descriptor)
        except ValueError:raise ValueError('INVALID_RUN_BINDING') from None
    for key in ('tasks_sha256','catalog_sha256','gold_file_sha256','scoring_gold_sha256','evidence_policy_sha256','adapter_sha256','prompt_sha256'):
        require(sha256(value[key]),'INVALID_BINDING_HASH')
    require(value['prompt_text'] is None or isinstance(value['prompt_text'],str))
    require(value['prompt_sha256']==digest(value['prompt_text']),'BINDING_PROMPT_HASH_MISMATCH')
    for key in ('adapter_path','python_executable','python_executable_resolved'):
        require(absolute_path(value[key]),'INVALID_BINDING_PATH')
    require(value['launch_command']==[value['python_executable'],value['adapter_path']],'BINDING_COMMAND_MISMATCH')
    require(nonempty(value['python']) and nonempty(value['platform']))
    hashes=value['runner_source_sha256']
    require(isinstance(hashes,dict) and bool(hashes) and all(isinstance(k,str) and re.fullmatch(r'[A-Za-z0-9_]+\.py',k) and sha256(v) for k,v in hashes.items()))
    execution=value['execution']
    require(isinstance(execution,dict) and set(execution)=={'cwd','dependency_files_sha256','dependency_package_versions','safe_environment','other_environment'},'INVALID_BINDING_EXECUTION')
    require(absolute_path(execution['cwd']),'INVALID_BINDING_PATH')
    files=execution['dependency_files_sha256'];packages=execution['dependency_package_versions'];env=execution['safe_environment']
    require(isinstance(files,dict) and all(absolute_path(k) and sha256(v) for k,v in files.items()),'INVALID_BINDING_DEPENDENCIES')
    require(isinstance(packages,dict) and all(nonempty(k) and nonempty(v) for k,v in packages.items()),'INVALID_BINDING_DEPENDENCIES')
    require(isinstance(env,dict) and set(env)==SAFE_ENV and all(v is None or (isinstance(v,str) and '\x00' not in v) for v in env.values()),'INVALID_BINDING_ENVIRONMENT')
    require(execution['other_environment']==ENVIRONMENT_SCOPE and value['retry_policy']==RETRY_POLICY and value['adapter_dependencies']==DEPENDENCY_SCOPE)
    disclosure=value['disclosure']
    if disclosure!=UNKNOWN_DISCLOSURE:
        validate_disclosure(disclosure,value['track'])
        for field,key in (('input_task_sha256','tasks_sha256'),('catalog_sha256','catalog_sha256')):
            require(field not in disclosure or disclosure[field]==value[key],'DISCLOSURE_BINDING_MISMATCH: '+field)
        if 'time_limit_seconds_per_case' in disclosure:
            require(positive_finite(disclosure['time_limit_seconds_per_case']) and disclosure['time_limit_seconds_per_case']==value['timeout_seconds'],'DISCLOSURE_BINDING_MISMATCH: timeout')
        if 'task_subset' in disclosure:require(disclosure['task_subset'] in ('all','development','evaluation'),'DISCLOSURE_BINDING_MISMATCH: task_subset')
    if tasks is not None:
        expected={t['id']:response_descriptor(t) for t in tasks}
        require(ids==[t['id'] for t in tasks] and value['tasks_sha256']==digest(tasks) and digest(descriptors)==digest(expected),'BINDING_TASK_MISMATCH')
        if 'task_subset' in disclosure:
            splits={t['split'] for t in tasks};subset=next(iter(splits)) if len(splits)==1 else 'all'
            require(disclosure['task_subset']==subset,'DISCLOSURE_BINDING_MISMATCH: task_subset')
    return value
