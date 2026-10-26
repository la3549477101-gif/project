"""Validate builds and keep immutable runtime copies separate from build output."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
import zipfile


@dataclass(frozen=True)
class RuntimePack:
    jar: Path
    frontend: Path
    warning: str = ''


def file_hash(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def atomic_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name('.'+path.name+'-'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('w',encoding='utf-8') as stream:
            json.dump(data,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)


def validate_jar(path):
    try:
        with zipfile.ZipFile(path) as jar:
            names=set(jar.namelist());manifest=jar.read('META-INF/MANIFEST.MF').decode('utf-8',errors='replace')
            if 'org.springframework.boot.loader.launch.JarLauncher' not in manifest or 'BOOT-INF/classes/com/example/odmtracker/OdmTrackerApplication.class' not in names or not any(n.startswith('BOOT-INF/lib/') for n in names):
                raise ValueError('not a packaged application')
            if jar.testzip() is not None:raise ValueError('CRC mismatch')
        return True
    except (OSError,ValueError,KeyError,zipfile.BadZipFile) as exc:
        raise RuntimeError('后端运行包不完整，可能还在构建中。请完成构建后再启动。') from exc


def frontend_hash(directory):
    directory=Path(directory)
    if not (directory/'index.html').is_file():raise RuntimeError('前端尚未构建，请先生成网页版本。')
    html=(directory/'index.html').read_text(encoding='utf-8')
    references=re.findall(r'(?:src|href)=["\']/?(assets/[^"\']+)["\']',html)
    if not references or not any(r.endswith('.js') for r in references):raise RuntimeError('网页入口缺少构建资源，请重新构建前端。')
    for reference in references:
        target=(directory/reference).resolve()
        if not target.is_relative_to(directory.resolve()) or not target.is_file():raise RuntimeError('网页资源不完整，请重新构建前端。')
    digest=hashlib.sha256()
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():raise RuntimeError('网页构建目录包含链接，请使用完整的本地构建。')
        if path.is_file():digest.update(path.relative_to(directory).as_posix().encode());digest.update(bytes.fromhex(file_hash(path)))
    return digest.hexdigest()


def previous_runtime(cache):
    cache=Path(cache)
    try:
        data=json.loads((cache/'last-runtime.json').read_text(encoding='utf-8'))
        jar=(cache/data['jar']).resolve();front=(cache/data['frontend']).resolve()
        if jar.parent!=cache.resolve() or front.parent!=cache.resolve():return None
        validate_jar(jar)
        if file_hash(jar)!=data['jar_hash'] or frontend_hash(front)!=data['frontend_hash']:return None
        return RuntimePack(jar,front)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):return None


def mark_runtime_ready(pack,cache):
    cache=Path(cache).resolve()
    if pack.jar.resolve().parent!=cache or pack.frontend.resolve().parent!=cache:raise RuntimeError('运行快照目录无效')
    validate_jar(pack.jar)
    atomic_json(cache/'last-runtime.json',{'jar':pack.jar.name,'frontend':pack.frontend.name,'jar_hash':file_hash(pack.jar),'frontend_hash':frontend_hash(pack.frontend)})


def prepare_runtime(jar_source,frontend_source,cache):
    jar_source=Path(jar_source);frontend_source=Path(frontend_source);cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    try:
        validate_jar(jar_source);jar_digest=file_hash(jar_source);front_digest=frontend_hash(frontend_source)
        jar=cache/('backend-'+jar_digest[:20]+'.jar')
        if jar.exists() and file_hash(jar)!=jar_digest:jar=jar.with_stem(jar.stem+'-'+uuid.uuid4().hex[:8])
        if not jar.exists():
            temporary=cache/('.backend-'+uuid.uuid4().hex+'.tmp')
            try:
                shutil.copyfile(jar_source,temporary);validate_jar(temporary)
                if file_hash(temporary)!=jar_digest:raise RuntimeError('后端正在构建，请稍后重试。')
                os.replace(temporary,jar)
            finally:temporary.unlink(missing_ok=True)
        front=cache/('frontend-'+front_digest[:20])
        if front.exists():
            try:reusable=frontend_hash(front)==front_digest
            except (OSError,ValueError,RuntimeError):reusable=False
            if not reusable:front=front.with_name(front.name+'-'+uuid.uuid4().hex[:8])
        if not front.exists():
            temporary=cache/('.frontend-'+uuid.uuid4().hex)
            try:
                shutil.copytree(frontend_source,temporary)
                if frontend_hash(temporary)!=front_digest:raise RuntimeError('前端正在构建，请稍后重试。')
                os.replace(temporary,front)
            finally:
                if temporary.exists() and temporary.parent.resolve()==cache.resolve():shutil.rmtree(temporary)
        return RuntimePack(jar,front)
    except (OSError,ValueError,RuntimeError) as exc:
        previous=previous_runtime(cache)
        if previous:return RuntimePack(previous.jar,previous.frontend,'新版本尚未完整准备，已使用上一次完整运行版本。原因：'+str(exc))
        raise RuntimeError(str(exc)) from exc
