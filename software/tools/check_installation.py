"""Install the exact delivery wheel and an offline rebuild of its exact sdist."""
from pathlib import Path
import subprocess,sys,tempfile,venv,json,os,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cardiobench import __version__
from cardiobench.core import distribution_verify
from cardiobench.runner import atomic_json
from cardiobench.artifacts import validate_packages,validate_package,extract_package,sha
from cardiobench.installation_evidence import FORMAT_VERSION,validate_installation
from cardiobench.build_environment import preflight_builder
ROOT=Path(__file__).resolve().parents[1]

def installed_check(wheel,temp):
    env=temp/'env';venv.EnvBuilder(with_pip=True).create(env)
    python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    environment=dict(os.environ);environment.pop('PYTHONPATH',None);environment.pop('PYTHONHOME',None)
    subprocess.run([str(python),'-m','pip','install','--no-index','--no-deps',str(wheel)],cwd=temp,env=environment,check=True,capture_output=True,text=True)
    code="import json,hashlib,importlib.metadata;from cardiobench import __version__;from cardiobench.core import ROOT;print(json.dumps({'module_version':__version__,'installed_version':importlib.metadata.version('nhanes-cardiobench'),'installed_core_manifest_sha256':hashlib.sha256((ROOT/'MANIFEST_SHA256.json').read_bytes()).hexdigest()}))"
    identity=json.loads(subprocess.run([str(python),'-c',code],cwd=temp,env=environment,check=True,capture_output=True,text=True).stdout)
    if identity['module_version']!=__version__ or identity['installed_version']!=__version__ or identity['installed_core_manifest_sha256']!=sha(ROOT/'MANIFEST_SHA256.json'):raise ValueError('INSTALLED_PACKAGE_BINDING_MISMATCH')
    console=env/('Scripts/cardiobench.exe' if os.name=='nt' else 'bin/cardiobench')
    commands=[('module_verify',[str(python),'-m','cardiobench','verify']),
      ('module_reproduce',[str(python),'-m','cardiobench','reproduce','--out',str(temp/'module_results')]),
      ('source_parse',[str(python),'-m','cardiobench.sources']),('console_help',[str(console),'--help']),
      ('console_verify',[str(console),'verify']),('console_reproduce',[str(console),'reproduce','--out',str(temp/'console_results')])];logs=[]
    for name,command in commands:
        done=subprocess.run(command,cwd=temp,env=environment,text=True,capture_output=True,check=True)
        logs.append({'id':name,'command':command,'returncode':done.returncode,'stdout':done.stdout,'stderr':done.stderr})
    return {'report_format_version':FORMAT_VERSION,'status':'passed','version':__version__,'python':sys.version,'platform':sys.platform,
      'python_executable':str(python),'console_executable':str(console),**identity,'checks':logs}

def check(package_dir,out,sdist_out):
    from cardiobench.io_safety import guard_output,aliases
    builder=preflight_builder(ROOT)
    distribution_verify();package_dir=Path(package_dir).resolve();packages=validate_packages(ROOT,package_dir)
    inputs=[package_dir/info['filename'] for info in packages.values()]
    for dest in [out,sdist_out]:guard_output(dest,inputs)
    if aliases(out,sdist_out):raise ValueError('OUTPUT_INPUT_COLLISION')
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td);direct=temp/'direct';direct.mkdir()
        direct_report=installed_check(package_dir/packages['wheel']['filename'],direct);direct_report.update(package=packages['wheel'],builder_environment=builder)
        extracted=temp/'source';extracted.mkdir()
        extract_package(package_dir/packages['sdist']['filename'],extracted)
        source=next(extracted.iterdir());built=temp/'rebuilt';built.mkdir()
        build_command=[sys.executable,'-m','pip','wheel','--no-index','--no-build-isolation','--no-deps','--wheel-dir',str(built),str(source)]
        build=subprocess.run(build_command,cwd=temp,text=True,capture_output=True,check=True)
        wheels=list(built.glob('*.whl'))
        if len(wheels)!=1:raise ValueError('SDIST_REBUILD_WHEEL_COUNT')
        rebuilt_identity=validate_package(wheels[0],ROOT);rebuilt=temp/'rebuilt-check';rebuilt.mkdir()
        sdist_report=installed_check(wheels[0],rebuilt)
        sdist_report.update(package=packages['sdist'],builder_environment=builder,rebuilt_wheel=rebuilt_identity,build_command=build_command,build_returncode=build.returncode,build_stdout=build.stdout,build_stderr=build.stderr)
        validate_installation(ROOT,direct_report,'wheel');validate_installation(ROOT,sdist_report,'sdist')
        # Write neither success report unless both installation paths passed.
        atomic_json(out,direct_report);atomic_json(sdist_out,sdist_report)
    return {'status':'passed','version':__version__,'packages':packages}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--package-dir',default=str(ROOT/'packages'));parser.add_argument('--out',default=str(ROOT/'results/ci/installation.json'));parser.add_argument('--sdist-out',default=str(ROOT/'results/ci/sdist_build.json'));args=parser.parse_args()
    try:result=check(args.package_dir,args.out,args.sdist_out)
    except subprocess.CalledProcessError as e:parser.exit(2,format_command_failure(e)+'\n')
    except (ValueError,OSError) as e:parser.exit(2,str(e)+'\n')
    print(json.dumps(result))
def format_command_failure(error):
    return str(error)+'\nstdout:\n'+(error.stdout or '')+'\nstderr:\n'+(error.stderr or '')

if __name__=='__main__':main()
