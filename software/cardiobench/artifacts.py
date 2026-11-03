"""Validate complete deliveries, including package identity; not a signature."""
from pathlib import Path,PurePosixPath,PureWindowsPath
import hashlib,zipfile,tarfile,email.parser,re,configparser,csv,io,base64
from . import __version__

DIRECTORIES=('packages','validation','review_materials')
PROFILE='complete-delivery-v8'
HISTORICAL_VERSIONS=frozenset({'v0_3_1','v0_4_0','v0_4_1','v0_4_2','v0_4_3','v0_4_4','v0_4_5','v0_4_6','v0_4_7'})
PACKAGE_STEM='nhanes_cardiobench-'+__version__
REQUIRES_PYTHON='>=3.10'
REQUIRED_FILES=('validation/installation.json','validation/sdist_build.json','validation/release_gate.json',
 'validation/resume_validation.json','validation/process_timing.json',
 'review_materials/reviewer_inputs.json','review_materials/reviewer_A.csv','review_materials/reviewer_B.csv',
 'review_materials/adjudication.csv','review_materials/expected_answers_after_review.json','review_materials/README.txt',
 'validation/resume_first_checkpoint.json','validation/resume_run/checkpoint.json',
 'validation/process_reproduction/paper_results.json','validation/process_reproduction/reference_predictions.json',
 'validation/process_reproduction/lexical_predictions.json',
 'validation/resume_run/predictions.json','validation/resume_run/traces.json',
 'validation/resume_run/score.json','validation/resume_run/run_manifest.json',
 'validation/process_reproduction/context_lexical_predictions.json','validation/process_reproduction/check_results.csv')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def inventory(root):
    files={}
    for name in DIRECTORIES:
        folder=Path(root)/name
        if folder.is_symlink():raise ValueError('ARTIFACT_SYMLINK_FORBIDDEN')
        for path in sorted(folder.rglob('*')):
            if path.is_symlink():raise ValueError('ARTIFACT_SYMLINK_FORBIDDEN')
            if path.is_file():files[path.relative_to(root).as_posix()]=sha(path)
    return files

def _metadata(raw):
    value=email.parser.BytesParser().parsebytes(raw)
    if len(value.get_all('Name',[]))!=1 or len(value.get_all('Version',[]))!=1:raise ValueError('PACKAGE_METADATA_INVALID')
    if re.sub(r'[-_.]+','-',value['Name']).lower()!='nhanes-cardiobench' or value['Version']!=__version__:raise ValueError('PACKAGE_VERSION_OR_NAME_MISMATCH')
    if value.get_all('Requires-Python')!=[REQUIRES_PYTHON] or value.get_all('Requires-Dist',[]):raise ValueError('PACKAGE_REQUIREMENTS_MISMATCH')

def member_name(name):
    """A portable, canonical archive path; reject Windows as well as POSIX roots."""
    if not isinstance(name,str) or not name or '\\' in name or ':' in name or '\x00' in name:
        raise ValueError('PACKAGE_MEMBER_INVALID')
    parts=name.split('/')
    if PurePosixPath(name).is_absolute() or PureWindowsPath(name).drive or PureWindowsPath(name).root or any(p in ('','.','..') for p in parts):
        raise ValueError('PACKAGE_MEMBER_INVALID')
    reserved=re.compile(r'^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)',re.I)
    if any(p.endswith((' ','.')) or reserved.match(p) or any(ord(c)<32 or c in '<>"|?*' for c in p) for p in parts):
        raise ValueError('PACKAGE_MEMBER_INVALID')
    return name

def _archive(path):
    """Validate all paths and links before any installation extraction."""
    path=Path(path);result={};seen={}
    def add(name,raw,directory=False):
        name=member_name(name[:-1] if directory and name.endswith('/') else name)
        key=name.casefold()
        if key in seen:raise ValueError('PACKAGE_MEMBER_COLLISION')
        if any(seen.get('/'.join(key.split('/')[:i])) is False for i in range(1,len(key.split('/')))):
            raise ValueError('PACKAGE_MEMBER_COLLISION')
        if not directory and any(k.startswith(key+'/') for k in seen):raise ValueError('PACKAGE_MEMBER_COLLISION')
        seen[key]=directory
        if not directory:result[name]=raw
    try:
        if path.suffix=='.whl':
            with zipfile.ZipFile(path) as stream:
                for info in stream.infolist():
                    if (info.external_attr>>16)&0o170000==0o120000:raise ValueError('PACKAGE_LINK_FORBIDDEN')
                    add(info.filename,None if info.is_dir() else stream.read(info),info.is_dir())
        else:
            with tarfile.open(path,'r:gz') as stream:
                for info in stream.getmembers():
                    if not (info.isdir() or info.isfile()):raise ValueError('PACKAGE_LINK_FORBIDDEN')
                    add(info.name,None if info.isdir() else stream.extractfile(info).read(),info.isdir())
    except (zipfile.BadZipFile,tarfile.TarError,EOFError,OSError) as exc:raise ValueError('PACKAGE_ARCHIVE_INVALID: '+str(exc)) from None
    return result

def extract_package(path,destination):
    """Read/validate the entire archive, then check containment at every write."""
    files=_archive(Path(path));root=Path(destination).resolve()
    for name,data in files.items():
        target=(root/name).resolve()
        if target==root or root not in target.parents:raise ValueError('PACKAGE_EXTRACTION_ESCAPE')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    return files

def validate_wheel_metadata(files,metadata,expected):
    """Validate the installed interface and RECORD, not only module source."""
    folder=metadata.rsplit('/',1)[0]
    required={folder+'/'+name for name in ('METADATA','WHEEL','RECORD','entry_points.txt')}
    if not required<=set(files):raise ValueError('WHEEL_METADATA_MISSING')
    allowed=expected|{folder+'/'+name for name in ('METADATA','WHEEL','RECORD','entry_points.txt','top_level.txt','licenses/LICENSE')}
    if not set(files)<=allowed:raise ValueError('WHEEL_UNEXPECTED_MEMBER')
    wheel=email.parser.BytesParser().parsebytes(files[folder+'/WHEEL'])
    if wheel.get_all('Wheel-Version')!=['1.0'] or wheel.get_all('Root-Is-Purelib')!=['true'] or wheel.get_all('Tag')!=['py3-none-any']:
        raise ValueError('WHEEL_TAG_OR_LAYOUT_MISMATCH')
    parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str
    try:parser.read_string(files[folder+'/entry_points.txt'].decode('utf-8'))
    except (UnicodeError,configparser.Error):raise ValueError('WHEEL_ENTRY_POINT_INVALID') from None
    if parser.defaults() or parser.sections()!=['console_scripts'] or dict(parser['console_scripts'])!={'cardiobench':'cardiobench.__main__:main'}:
        raise ValueError('WHEEL_ENTRY_POINT_MISMATCH')
    try:rows=list(csv.reader(io.StringIO(files[folder+'/RECORD'].decode('utf-8'),newline=''),strict=True))
    except (UnicodeError,csv.Error):raise ValueError('WHEEL_RECORD_INVALID') from None
    if any(len(r)!=3 for r in rows) or len(rows)!=len(files) or {r[0] for r in rows}!=set(files):raise ValueError('WHEEL_RECORD_COVERAGE_MISMATCH')
    for name,checksum,size in rows:
        if name==folder+'/RECORD':
            if checksum or size:raise ValueError('WHEEL_RECORD_INVALID')
        else:
            expected_hash='sha256='+base64.urlsafe_b64encode(hashlib.sha256(files[name]).digest()).rstrip(b'=').decode('ascii')
            if checksum!=expected_hash or size!=str(len(files[name])):raise ValueError('WHEEL_RECORD_HASH_MISMATCH')

def validate_release_hygiene(root):
    """Reject current process residue; explicitly versioned history is immutable."""
    for directory in DIRECTORIES:
        for path in (Path(root)/directory).rglob('*'):
            relative=path.relative_to(Path(root)/directory)
            if relative.parts and relative.parts[0] in HISTORICAL_VERSIONS:continue
            if path.name=='run.lock' or path.name.endswith(('.tmp','.part','.partial')):
                raise ValueError('TRANSIENT_DELIVERY_FILE: '+path.relative_to(root).as_posix())

def validate_sdist_metadata(files,top,expected):
    """Permit only the reviewed core and explicit setuptools-generated metadata."""
    prefix=top+'/'
    egg=prefix+'nhanes_cardiobench.egg-info/'
    generated={prefix+'PKG-INFO',prefix+'setup.cfg'}|{egg+n for n in (
        'PKG-INFO','SOURCES.txt','dependency_links.txt','entry_points.txt','top_level.txt')}
    if not set(files)<=expected|generated:raise ValueError('SDIST_UNEXPECTED_MEMBER')
    if egg+'PKG-INFO' in files:
        _metadata(files[egg+'PKG-INFO'])
        if files[egg+'PKG-INFO']!=files[prefix+'PKG-INFO']:raise ValueError('SDIST_METADATA_MISMATCH')
    for name,content in [('dependency_links.txt',''),('top_level.txt','cardiobench')]:
        if egg+name in files:
            try:actual=files[egg+name].decode('utf-8').strip()
            except UnicodeError:raise ValueError('SDIST_METADATA_INVALID') from None
            if actual!=content:raise ValueError('SDIST_METADATA_MISMATCH')
    for name,sections,items in [(prefix+'setup.cfg',['egg_info'],{'tag_build':'','tag_date':'0'}),
        (egg+'entry_points.txt',['console_scripts'],{'cardiobench':'cardiobench.__main__:main'})]:
        if name not in files:continue
        parser=configparser.ConfigParser(interpolation=None);parser.optionxform=str
        try:parser.read_string(files[name].decode('utf-8'))
        except (UnicodeError,configparser.Error):raise ValueError('SDIST_CONFIGURATION_INVALID') from None
        if parser.defaults() or parser.sections()!=sections or dict(parser[sections[0]])!=items:
            raise ValueError('SDIST_CONFIGURATION_MISMATCH')
    if egg+'SOURCES.txt' in files:
        try:rows=files[egg+'SOURCES.txt'].decode('utf-8').splitlines()
        except UnicodeError:raise ValueError('SDIST_SOURCES_INVALID') from None
        named={prefix+member_name(n) for n in rows}
        if len(named)!=len(rows) or not expected<=named or not named<=set(files):
            raise ValueError('SDIST_SOURCES_MISMATCH')

def validate_package(path,root):
    from .core import read_json
    path=Path(path);root=Path(root)
    expected_name=PACKAGE_STEM+('-py3-none-any.whl' if path.suffix=='.whl' else '.tar.gz')
    if path.name!=expected_name:raise ValueError('PACKAGE_FILENAME_MISMATCH')
    files=_archive(path)
    manifest=(root/'MANIFEST_SHA256.json').read_bytes();core=read_json(root/'MANIFEST_SHA256.json')
    if core.get('version')!=__version__:raise ValueError('PACKAGE_CORE_VERSION_MISMATCH')
    if path.suffix=='.whl':
        metas=[n for n in files if n.endswith('.dist-info/METADATA')]
        if len(metas)!=1:raise ValueError('PACKAGE_METADATA_INVALID')
        metadata=metas[0];embedded='cardiobench/_release/MANIFEST_SHA256.json'
        if metadata!=PACKAGE_STEM+'.dist-info/METADATA':raise ValueError('WHEEL_DIST_INFO_MISMATCH')
        def location(name):return name if name.startswith('cardiobench/') else 'cardiobench/_release/'+name
    else:
        tops={name.split('/')[0] for name in files}
        if len(tops)!=1:raise ValueError('PACKAGE_ROOT_INVALID')
        top=next(iter(tops));metadata=top+'/PKG-INFO';embedded=top+'/MANIFEST_SHA256.json'
        if top!=PACKAGE_STEM:raise ValueError('SDIST_ROOT_MISMATCH')
        def location(name):return top+'/'+name
    if metadata not in files:raise ValueError('PACKAGE_METADATA_INVALID')
    _metadata(files[metadata])
    if files.get(embedded)!=manifest:raise ValueError('PACKAGE_CORE_MANIFEST_MISMATCH')
    for name,digest in core['files'].items():
        data=files.get(location(name))
        if data is None or hashlib.sha256(data).hexdigest()!=digest:raise ValueError('PACKAGE_CORE_FILE_MISMATCH: '+name)
    expected={location(n) for n in core['files']}|{embedded}
    if path.suffix=='.whl':validate_wheel_metadata(files,metadata,expected)
    else:validate_sdist_metadata(files,top,expected)
    return {'filename':path.name,'sha256':sha(path),'version':__version__,'core_manifest_sha256':sha(root/'MANIFEST_SHA256.json'),'core_files_verified':len(core['files'])}

def validate_packages(root,package_dir=None):
    root=Path(root);folder=Path(package_dir) if package_dir else root/'packages'
    if not folder.is_dir() or folder.is_symlink():raise ValueError('REQUIRED_PACKAGES_MISSING')
    paths=list(folder.iterdir());wheels=[p for p in paths if p.suffix=='.whl'];sources=[p for p in paths if p.name.endswith('.tar.gz')]
    if len(paths)!=2 or len(wheels)!=1 or len(sources)!=1 or any(not p.is_file() or p.is_symlink() for p in paths):raise ValueError('EXPECTED_ONE_WHEEL_AND_SDIST')
    return {'wheel':validate_package(wheels[0],root),'sdist':validate_package(sources[0],root)}

def validate_delivery(root):
    from .core import read_json
    from .runner import digest
    root=Path(root)
    validate_release_hygiene(root)
    for name in REQUIRED_FILES:
        if not (root/name).is_file():raise ValueError('REQUIRED_DELIVERY_FILE_MISSING: '+name)
    packages=validate_packages(root);core_hash=sha(root/'MANIFEST_SHA256.json')
    from .installation_evidence import validate_installation
    for name,kind in [('installation.json','wheel'),('sdist_build.json','sdist')]:
        report=read_json(root/'validation'/name)
        if not isinstance(report,dict):raise ValueError('INSTALLATION_EVIDENCE_MUST_BE_OBJECT: '+name)
        if report.get('status')!='passed' or report.get('version')!=__version__ or report.get('package')!=packages[kind] or report.get('installed_version')!=__version__ or report.get('installed_core_manifest_sha256')!=core_hash:raise ValueError('INSTALLATION_EVIDENCE_BINDING_MISMATCH: '+name)
        validate_installation(root,report,kind)
    from .delivery_evidence import validate_evidence
    try:validate_evidence(root)
    except (KeyError,TypeError,OverflowError) as exc:raise ValueError('INVALID_DELIVERY_EVIDENCE: '+str(exc)) from None
    return {'profile':PROFILE,'packages':packages,'required_files_verified':len(REQUIRED_FILES)}

def freeze_artifacts(root):
    from .core import distribution_verify
    # Core bytes and package contents must already be final; never generate missing evidence.
    root=Path(root);distribution_verify(root);validate_delivery(root)
    import json
    value={'version':__version__,'profile':PROFILE,'algorithm':'sha256','core_manifest_sha256':sha(root/'MANIFEST_SHA256.json'),'files':inventory(root)}
    (root/'ARTIFACTS_SHA256.json').write_bytes((json.dumps(value,indent=2)+'\n').encode('utf-8'))
    return value

def verify_artifacts(root,require=False):
    from .core import read_json
    root=Path(root);manifest=root/'ARTIFACTS_SHA256.json';actual=inventory(root)
    if not manifest.is_file():
        if require or actual:raise ValueError('ARTIFACT_MANIFEST_MISSING')
        return {'status':'not bundled','scope':'core source/resources verified; outer delivery evidence is not installed'}
    saved=read_json(manifest)
    if set(saved)!={'version','profile','algorithm','core_manifest_sha256','files'} or saved['version']!=__version__ or saved['profile']!=PROFILE or saved['algorithm']!='sha256':raise ValueError('INVALID_ARTIFACT_MANIFEST')
    if saved['core_manifest_sha256']!=sha(root/'MANIFEST_SHA256.json'):raise ValueError('ARTIFACT_CORE_BINDING_MISMATCH')
    if not isinstance(saved['files'],dict) or saved['files']!=actual:raise ValueError('ARTIFACT_HASH_OR_COVERAGE_MISMATCH')
    delivery=validate_delivery(root)
    return {'status':'verified','files':len(actual),'core_manifest_bound':True,**delivery,'authentication':'checksums and report bindings detect inconsistency; no external signature or trust anchor'}
