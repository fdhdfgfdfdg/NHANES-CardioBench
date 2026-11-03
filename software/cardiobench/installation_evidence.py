"""Check the contents of installation observations; these are not attestations."""
from pathlib import Path
import re
from . import __version__
from .core import read_json,parse_json,reference,lexical,run_builtin,summarize

CHECK_IDS=('module_verify','module_reproduce','source_parse','console_help','console_verify','console_reproduce')
FORMAT_VERSION=3

def require(ok,message):
    if not ok:raise ValueError(message)

def expected_observations(root):
    root=Path(root);data=root/'cardiobench/data'
    tasks=read_json(data/'tasks.json');gold=read_json(data/'gold.json');catalog=read_json(data/'catalog.json')
    from .__main__ import mutations
    from .runner import file_hash
    core=read_json(root/'MANIFEST_SHA256.json')
    parsed={'components':len({v['file'] for v in catalog['variables']}),'variable_occurrences':len(catalog['variables']),
      'section_hash_scheme':'sha256 of HTMLParser section text; whitespace collapsed, UTF-8; v1','parsed_metadata_equal':True}
    from .verification_evidence import core_observations,NOT_BUNDLED
    verification={**core_observations(root),'artifact_verification':dict(NOT_BUNDLED)}
    sem=[t for t in tasks if t['kind']=='semantic']
    # Recompute finite-inventory summaries; no timings or environment claims are inferred.
    predictions,_=run_builtin(tasks,catalog,reference);retrieved,_=run_builtin(sem,catalog,lexical)
    mutation=mutations(tasks,gold)
    reproduction={'reference':summarize(tasks,gold,predictions)['overall'],
      'lexical_semantic':summarize(sem,gold,retrieved)['overall'],'mutations':{k:v for k,v in mutation.items() if k!='rows'}}
    return verification,reproduction,parsed

def validate_installation(root,report,kind):
    from .runner import digest,file_hash
    require(isinstance(report,dict) and type(report.get('report_format_version')) is int and report['report_format_version']==FORMAT_VERSION,'INSTALLATION_REPORT_FORMAT')
    from .build_environment import validate_builder
    validate_builder(root,report.get('builder_environment'))
    require(report.get('module_version')==__version__ and all(isinstance(report.get(k),str) and report[k].strip() for k in ('python','platform','python_executable','console_executable')),'INSTALLATION_ENVIRONMENT_MISSING')
    checks=report.get('checks')
    require(isinstance(checks,list) and len(checks)==len(CHECK_IDS) and all(isinstance(c,dict) for c in checks) and [c.get('id') for c in checks]==list(CHECK_IDS),'INSTALLATION_CHECKS_INCOMPLETE')
    verification,reproduction,parsed=expected_observations(root)
    for check in checks:
        require(set(check)=={'id','command','returncode','stdout','stderr'} and type(check.get('returncode')) is int and check['returncode']==0 and isinstance(check.get('stdout'),str) and isinstance(check.get('stderr'),str),'INSTALLATION_COMMAND_FAILED')
        name=check['id'];command=check['command']
        require(isinstance(command,list) and all(isinstance(x,str) and x for x in command),'INSTALLATION_COMMAND_MISMATCH')
        prefix=[report['console_executable']] if name.startswith('console_') else [report['python_executable'],'-m']
        if name=='source_parse':expected=prefix+['cardiobench.sources']
        elif name=='console_help':expected=prefix+['--help']
        else:
            expected=prefix+([] if name.startswith('console_') else ['cardiobench'])
            expected+=['verify'] if name.endswith('verify') else ['reproduce','--out',command[-1] if command else '']
        require(command==expected,'INSTALLATION_COMMAND_MISMATCH')
        if name=='console_help':
            require(all(token in check['stdout'] for token in ('usage:','verify','reproduce','run-adapter','--help')),'INSTALLATION_CONSOLE_HELP_INVALID')
            continue
        value=parse_json(check['stdout'])
        if name.endswith('verify'):require(digest(value)==digest(verification),'INSTALLATION_VERIFY_RESULT_MISMATCH')
        elif name=='source_parse':require(digest(value)==digest(parsed),'INSTALLATION_SOURCE_RESULT_MISMATCH')
        else:require(isinstance(value,dict) and digest(value)==digest({**reproduction,'out':command[-1]}),'INSTALLATION_REPRODUCTION_MISMATCH')
    if kind=='sdist':
        rebuilt=report.get('rebuilt_wheel');core_hash=file_hash(Path(root)/'MANIFEST_SHA256.json')
        require(isinstance(rebuilt,dict) and set(rebuilt)=={'filename','sha256','version','core_manifest_sha256','core_files_verified'} and
          rebuilt.get('filename')=='nhanes_cardiobench-'+__version__+'-py3-none-any.whl' and isinstance(rebuilt.get('sha256'),str) and re.fullmatch('[0-9a-f]{64}',rebuilt['sha256']) is not None and
          rebuilt.get('version')==__version__ and rebuilt.get('core_manifest_sha256')==core_hash and type(rebuilt.get('core_files_verified')) is int and rebuilt['core_files_verified']==verification['distribution_files_verified'],'SDIST_REBUILD_BINDING_MISSING')
        require(type(report.get('build_returncode')) is int and report['build_returncode']==0 and isinstance(report.get('build_stdout'),str) and report['build_stdout'].strip() and isinstance(report.get('build_stderr'),str),'SDIST_BUILD_RESULT_MISSING')
        command=report.get('build_command')
        require(isinstance(command,list) and len(command)==10 and all(isinstance(x,str) and x for x in command) and command[1:8]==['-m','pip','wheel','--no-index','--no-build-isolation','--no-deps','--wheel-dir'],'SDIST_BUILD_COMMAND_MISMATCH')
        require(command[0]==report['builder_environment']['python_executable'],'SDIST_BUILD_INTERPRETER_MISMATCH')
