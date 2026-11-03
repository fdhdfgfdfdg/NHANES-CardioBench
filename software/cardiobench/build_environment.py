"""Pinned build-tool preflight; ordinary runtime commands need none of these tools."""
from pathlib import Path
import hashlib, importlib.metadata, importlib.util, re, sys

def requirements(root):
    path=Path(root)/'requirements-build.txt';raw=path.read_bytes();pairs=[]
    for line in raw.decode('utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        match=re.fullmatch(r'(build|setuptools|wheel)==([0-9]+(?:\.[0-9]+)+)',line)
        if match is None:raise ValueError('INVALID_BUILD_REQUIREMENTS')
        pairs.append(match.groups())
    pinned=dict(pairs)
    if len(pairs)!=3 or set(pinned)!={'build','setuptools','wheel'}:raise ValueError('INVALID_BUILD_REQUIREMENTS')
    return pinned,hashlib.sha256(raw).hexdigest()

def preflight_builder(root):
    pinned,sha=requirements(root);versions={};problems=[]
    for name in ['pip',*pinned]:
        try:version=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:version=None
        if version is None or importlib.util.find_spec(name) is None:problems.append(name+' is not installed')
        elif name in pinned and version!=pinned[name]:problems.append(name+' requires '+pinned[name]+', found '+version)
        versions[name]=version
    if problems:raise ValueError('BUILD_ENVIRONMENT_NOT_READY: '+'; '.join(problems)+'. Prepare this interpreter with python -m pip install -r requirements-build.txt before offline validation.')
    return {'python':sys.version,'python_executable':sys.executable,'tools':versions,'requirements_sha256':sha}

def validate_builder(root,value):
    from .binding_contract import absolute_path, nonempty
    pinned,sha=requirements(root)
    if not isinstance(value,dict) or set(value)!={'python','python_executable','tools','requirements_sha256'} or not nonempty(value['python']) or not absolute_path(value['python_executable']) or value['requirements_sha256']!=sha:
        raise ValueError('BUILD_ENVIRONMENT_EVIDENCE_MISMATCH')
    versions=value['tools']
    if not isinstance(versions,dict) or set(versions)!={'pip',*pinned} or not nonempty(versions['pip']) or any(versions[k]!=v for k,v in pinned.items()):raise ValueError('BUILD_ENVIRONMENT_EVIDENCE_MISMATCH')
    return value
