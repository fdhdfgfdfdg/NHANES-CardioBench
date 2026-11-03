"""Validate a recorded subprocess command and its sequential elapsed-time bound."""
from .binding_contract import absolute_path, positive_finite
from .core import parse_json
from .runner import digest
FORMAT_VERSION=1
SCOPE='fresh interpreter, release verification and report writing; excludes installation; verification_scope records whether outer delivery was checked'
FIELDS={'report_format_version','version','evidence_binding','seconds','command','python_executable','output_directory','returncode','stdout','stderr','verification_scope','scope','result','paper_results_sha256'}
def validate_process_record(report,timing):
    if not isinstance(report,dict) or set(report)!=FIELDS or type(report['report_format_version']) is not int or report['report_format_version']!=FORMAT_VERSION:raise ValueError('PROCESS_REPORT_FORMAT')
    if not absolute_path(report['python_executable']) or not absolute_path(report['output_directory']) or report['command']!=[report['python_executable'],'-m','cardiobench','reproduce','--out',report['output_directory']]:raise ValueError('PROCESS_COMMAND_MISMATCH')
    if type(report['returncode']) is not int or report['returncode']!=0 or not isinstance(report['stdout'],str) or not isinstance(report['stderr'],str) or report['scope']!=SCOPE:raise ValueError('PROCESS_COMMAND_RESULT_INVALID')
    if digest(parse_json(report['stdout']))!=digest(report['result']) or not isinstance(report['result'],dict) or report['result'].get('out')!=report['output_directory']:raise ValueError('PROCESS_STDOUT_MISMATCH')
    lower=sum(timing['warm_reference_raw_seconds'])+sum(timing[k] for k in ('reference_first_seconds','lexical_seconds','context_lexical_seconds'))
    tolerance=min(0.001,lower*0.001)
    if not positive_finite(report['seconds']) or report['seconds']+tolerance<lower:raise ValueError('PROCESS_ELAPSED_INCONSISTENT')
