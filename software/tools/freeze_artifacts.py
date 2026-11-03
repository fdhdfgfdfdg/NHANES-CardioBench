"""Freeze a complete, validated delivery after core and package bytes are final."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cardiobench.artifacts import freeze_artifacts
if __name__=='__main__':
    try:value=freeze_artifacts(ROOT)
    except (ValueError,OSError) as e:raise SystemExit(str(e)) from None
    print(json.dumps({'artifact_files':len(value['files']),'profile':value['profile']}))
