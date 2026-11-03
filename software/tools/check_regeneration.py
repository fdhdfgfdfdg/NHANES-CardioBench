"""Rebuild metadata and workloads in a temporary tree; never rewrite a release."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cardiobench.core import ROOT, DATA
from cardiobench.sources import parse_sources

def main():
    parsed=json.dumps(parse_sources(ROOT),indent=2).encode('utf-8')
    if parsed!=(ROOT/'sources/parsed_codebooks.json').read_bytes():raise ValueError('PARSED_BYTES_DIFFER')
    names=['tasks.json','gold.json','catalog.json','positive_control_routes.json','release.json','evidence_policy.json']
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);(root/'sources').mkdir();(root/'tools').mkdir();(root/'cardiobench/data').mkdir(parents=True)
        (root/'sources/parsed_codebooks.json').write_bytes(parsed)
        shutil.copy2(ROOT/'tools/curate_workloads.py',root/'tools/curate_workloads.py')
        shutil.copy2(ROOT/'tools/extension_workloads.py',root/'tools/extension_workloads.py')
        subprocess.run([sys.executable,str(root/'tools/curate_workloads.py')],check=True,capture_output=True,text=True)
        matches={name:(root/'cardiobench/data'/name).read_bytes()==(DATA/name).read_bytes() for name in names}
        if not all(matches.values()):raise ValueError('REGENERATION_DIFFERENCE: '+str(matches))
    print(json.dumps({'parsed_bytes_equal':True,'generated_files_byte_equal':matches,'network_used':False},indent=2))
if __name__=='__main__':main()
