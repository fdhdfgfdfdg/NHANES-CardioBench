"""Preflight accidental output collisions; not an adversarial filesystem sandbox."""
from pathlib import Path
from .core import ROOT, PACKAGE, read_json

def aliases(a,b):
    a,b=Path(a),Path(b)
    return a.resolve()==b.resolve() or (a.exists() and b.exists() and a.samefile(b))

def guard_output(path,inputs=()):
    path=Path(path)
    for source in inputs:
        if aliases(path,source):raise ValueError('OUTPUT_INPUT_COLLISION: '+str(path))
    protected=[ROOT/'MANIFEST_SHA256.json',ROOT/'ARTIFACTS_SHA256.json']
    for name in read_json(ROOT/'MANIFEST_SHA256.json')['files']:
        protected.append(PACKAGE.parent/name if ROOT.name=='_release' and name.startswith('cardiobench/') else ROOT/name)
    if any(aliases(path,p) for p in protected):raise ValueError('PROTECTED_RELEASE_OUTPUT: '+str(path))
    resolved=path.resolve()
    for directory in [PACKAGE,*[ROOT/d for d in ['sources','tests','tools','docs','examples','results/paper','results/v0_3_1','results/v0_4_0','results/v0_4_1','results/v0_4_2','results/v0_4_3','results/v0_4_4','results/v0_4_5','results/v0_4_6','results/v0_4_7','packages','validation','review_materials']]]:
        if resolved==directory.resolve() or directory.resolve() in resolved.parents:raise ValueError('PROTECTED_RELEASE_OUTPUT: '+str(path))

def guard_directory(path,inputs=()):
    guard_output(Path(path)/'checkpoint.json',inputs)
    for source in inputs:
        resolved=Path(source).resolve();dest=Path(path).resolve()
        if dest==resolved or dest in resolved.parents:raise ValueError('OUTPUT_CONTAINS_INPUT: '+str(source))


def atomic_bytes(path, data, inputs=()):
    import os, tempfile
    guard_output(path, inputs)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd, name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    temp=Path(name)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
        if os.name=='posix':
            parent=os.open(path.parent,os.O_RDONLY)
            try:os.fsync(parent)
            finally:os.close(parent)
    finally:
        temp.unlink(missing_ok=True)
