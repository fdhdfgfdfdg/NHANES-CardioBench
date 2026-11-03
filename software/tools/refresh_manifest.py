"""Maintainer-only release operation. Never called by verify or score."""
from pathlib import Path
import hashlib, json
ROOT=Path(__file__).resolve().parents[1]
files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
       for p in sorted(ROOT.rglob('*')) if p.is_file()
       and '__pycache__' not in p.parts and p.suffix!='.pyc'
       and p.name not in ('MANIFEST_SHA256.json','ARTIFACTS_SHA256.json')
       and not p.relative_to(ROOT).as_posix().startswith(('packages/','validation/','review_materials/','results/reproduced/','results/ci/','results/adapter/','build/','dist/','nhanes_cardiobench.egg-info/'))}
(ROOT/'MANIFEST_SHA256.json').write_bytes((json.dumps({'version':'0.4.8','algorithm':'sha256','files':files},indent=2)+'\n').encode('utf-8'))
