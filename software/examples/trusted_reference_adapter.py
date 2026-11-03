"""Trusted local positive-control adapter; never use it as a model competitor."""
import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cardiobench.core import reference
payload=json.load(sys.stdin)
print(json.dumps(reference(payload['task'],payload['catalog']),allow_nan=False))
