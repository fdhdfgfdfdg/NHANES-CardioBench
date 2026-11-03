"""Build the reviewed release evidence into wheel resources."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py

class BuildWithRelease(build_py):
    def run(self):
        super().run()
        root=Path(__file__).resolve().parent;dest=Path(self.build_lib)/'cardiobench/_release'
        if dest.exists():shutil.rmtree(dest)
        dest.mkdir(parents=True)
        import json
        files=json.loads((root/'MANIFEST_SHA256.json').read_text())['files']
        for name in [*files,'MANIFEST_SHA256.json']:
            if name.startswith('cardiobench/'):continue
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,target)
    def get_outputs(self,include_bytecode=1):
        outputs=super().get_outputs(include_bytecode)
        return outputs+[str(p) for p in (Path(self.build_lib)/'cardiobench/_release').rglob('*') if p.is_file()]
setup(cmdclass={'build_py':BuildWithRelease})
