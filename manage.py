"""Start/stop this local app without changing PowerShell execution policy."""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
import msvcrt
from contextlib import contextmanager
from launch_runtime import prepare_runtime, mark_runtime_ready, atomic_json, previous_runtime

APP = Path(__file__).resolve().parent
TOOLS = APP.parents[2] / '.tools'
LOGS = APP / 'logs'
STATE = LOGS / 'services.json'
URL = 'http://127.0.0.1:5173/'
RUNTIME = LOGS / 'runtime'
TICK_OFFSET = 504911232000000000  # .NET epoch -> Windows FILETIME epoch.
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
KERNEL = ctypes.WinDLL('kernel32', use_last_error=True)
KERNEL.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
KERNEL.OpenProcess.restype = wintypes.HANDLE
KERNEL.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
KERNEL.GetProcessTimes.restype = wintypes.BOOL
KERNEL.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
KERNEL.QueryFullProcessImageNameW.restype = wintypes.BOOL
KERNEL.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
KERNEL.GetExitCodeProcess.restype = wintypes.BOOL
KERNEL.CloseHandle.argtypes = [wintypes.HANDLE]


def specs(runtime=None):
    java = TOOLS / 'jdk-21.0.12.1+1/bin/java.exe'
    node = TOOLS / 'node-v24.22.1-win-x64/node.exe'
    python = APP / 'backend/flask/.venv/Scripts/python.exe'
    return {
        'springboot': ([str(java), '-jar', str(runtime.jar if runtime else APP / 'backend/springboot/target/odm-tracker-1.0.0.jar')], APP / 'backend/springboot'),
        'flask': ([str(python), '-m', 'flask', '--app', 'app', 'run', '--host', '127.0.0.1', '--port', '5000'], APP / 'backend/flask'),
        'frontend': ([str(python), str(APP / 'serve_frontend.py'), '--directory', str(runtime.frontend if runtime else APP / 'frontend/dist'), '--port', '5173'], APP),
    }


def identity(process_id):
    handle = KERNEL.OpenProcess(0x1000, False, process_id)
    if not handle:
        if ctypes.get_last_error() == 87:
            return None
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        exit_code = wintypes.DWORD()
        if not KERNEL.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            raise ctypes.WinError(ctypes.get_last_error())
        if exit_code.value != 259:
            return None
        creation, exit_time, kernel, user = (wintypes.FILETIME() for _ in range(4))
        if not KERNEL.GetProcessTimes(handle, *map(ctypes.byref, (creation, exit_time, kernel, user))):
            raise ctypes.WinError(ctypes.get_last_error())
        size = wintypes.DWORD(32768)
        image = ctypes.create_unicode_buffer(size.value)
        if not KERNEL.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        ticks = (creation.dwHighDateTime << 32) + creation.dwLowDateTime + TICK_OFFSET
        return str(ticks), os.path.normcase(os.path.abspath(image.value))
    finally:
        KERNEL.CloseHandle(handle)


def matches(service):
    current = identity(service['ProcessId'])
    if current is None:
        return False
    expected = specs().get(service['Name'])
    allowed={os.path.normcase(os.path.abspath(expected[0][0]))} if expected else set()
    if service['Name']=='frontend': allowed.add(os.path.normcase(os.path.abspath(TOOLS/'node-v24.22.1-win-x64/node.exe')))
    if not expected or current[0] != str(service['StartedUtcTicks']) or current[1] not in allowed:
        raise RuntimeError('进程身份与启动记录不一致，已保留该进程，请先检查日志。')
    return True


def read_state():
    if not STATE.exists():
        return []
    try:
        raw = STATE.read_bytes()
        text = raw.decode('utf-16') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8-sig')
        data = json.loads(text)
        rows=data if isinstance(data,list) else [data]
        names=set()
        for row in rows:
            if not isinstance(row,dict) or row.get('Name') not in specs() or row['Name'] in names or not isinstance(row.get('ProcessId'),int) or row['ProcessId']<=0 or not str(row.get('StartedUtcTicks','')).isdigit():raise ValueError('invalid state')
            names.add(row['Name'])
        return rows
    except (OSError,ValueError,UnicodeError,TypeError) as exc:
        raise RuntimeError('启动记录无法读取，已保留日志且未停止任何未知进程。请检查logs/services.json。') from exc


def stop_services(services):
    for service in reversed(services):
        if not matches(service):
            continue
        result = subprocess.run([str(Path(os.environ['SystemRoot']) / 'System32/taskkill.exe'),
            '/PID', str(service['ProcessId']), '/T', '/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode and matches(service):
            raise RuntimeError('Could not stop ' + service['Name'])
        deadline = time.monotonic() + 10
        while matches(service):
            if time.monotonic() > deadline:
                raise RuntimeError('Service did not stop: ' + service['Name'])
            time.sleep(.1)


def stop():
    stop_services(read_state())
    STATE.unlink(missing_ok=True)
    print('应用已停止，项目数据已保留。')


@contextmanager
def operation_lock():
    LOGS.mkdir(exist_ok=True)
    with (LOGS/'launcher.lock').open('a+b') as lock:
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError as exc:raise RuntimeError('应用正在启动、停止或更新，请稍等片刻再操作。') from exc
        try:yield
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


def healthy():
    try:
        with HTTP.open('http://127.0.0.1:8080/api/health',timeout=3) as response:
            if not json.load(response).get('databaseWritable'):return False,'数据库暂时不可写，请检查目录权限或占用情况。'
        with HTTP.open('http://127.0.0.1:5000/api/summary',timeout=3) as response:
            if 'projectCount' not in json.load(response):return False,'数据辅助服务响应异常。'
        with HTTP.open(URL+'__app_health__',timeout=3) as response:
            if json.load(response).get('app')!='odm-tracker-frontend':return False,'网页服务响应异常。'
        with HTTP.open(URL,timeout=3) as response:
            if b'assets/' not in response.read():return False,'网页资源未准备完成。'
        return True,''
    except (OSError,ValueError) as exc:return False,str(exc)


def status():
    services=read_state();active=[matches(service) for service in services]
    ok,message=healthy() if len(services)==3 and all(active) else (False,'有服务未运行，可再次双击原启动快捷方式自动恢复。')
    print(('应用正常：' if ok else '应用尚未就绪：')+(URL if ok else message))
    return ok


def start(no_browser):
    LOGS.mkdir(exist_ok=True)
    old = read_state()
    if old:
        active = [matches(service) for service in old]
        if any(active):
            ok,message=healthy() if len(old)==3 and all(active) else (False,'部分服务已停止')
            if ok:
                print('应用已在运行：'+URL)
                if not no_browser:webbrowser.open(URL)
                return
            print('正在恢复未就绪的应用服务…')
            stop_services(old)
        STATE.unlink(missing_ok=True)
    for port in (8080,5000,5173):
        try:
            with socket.socket() as probe:probe.bind(('127.0.0.1',port))
        except OSError as exc:raise RuntimeError(f'端口 {port} 已被其他程序占用，未关闭未知程序。请检查后重试。') from exc
    runtime=prepare_runtime(APP/'backend/springboot/target/odm-tracker-1.0.0.jar',APP/'frontend/dist',RUNTIME)
    if runtime.warning:print(runtime.warning)
    launch_with_recovery(runtime)
    print('应用已启动：'+URL)
    if not no_browser:webbrowser.open(URL)


def launch_with_recovery(runtime):
    previous=previous_runtime(RUNTIME)
    try:
        launch_runtime(runtime)
    except Exception as exc:
        if previous is None or (previous.jar==runtime.jar and previous.frontend==runtime.frontend):raise
        # launch_runtime cleans up its own processes before returning an error.
        # Preserve the failed attempt's logs before the one permitted retry.
        failure=LOGS/('failed-start-'+str(time.time_ns()))
        failure.mkdir()
        for name in specs():
            for suffix in ('.out.log','.err.log'):
                path=LOGS/(name+suffix)
                if path.exists():path.replace(failure/path.name)
        print('新版本启动失败，正在恢复上一次正常运行的版本。原因：'+str(exc))
        try:launch_runtime(previous)
        except Exception as recovery:
            raise RuntimeError('恢复启动仍未成功，请查看logs目录中的启动日志。新版本原因：'+str(exc)+'；恢复原因：'+str(recovery)) from recovery


def launch_runtime(runtime):
    definitions=specs(runtime)
    for command,_ in definitions.values():
        if not Path(command[0]).is_file():raise RuntimeError('运行环境缺失：'+command[0])
    env = dict(os.environ)
    env['PATH'] = os.pathsep.join([str(Path(definitions[name][0][0]).parent) for name in ('springboot', 'flask')] + [env.get('PATH', '')])
    env['JAVA_HOME'] = str(TOOLS / 'jdk-21.0.12.1+1')
    env['SPRING_API'] = 'http://127.0.0.1:8080/api'
    env['FLASK_DEBUG'] = '0'
    temporary = LOGS / 'tmp'
    temporary.mkdir(exist_ok=True)
    env['TEMP'] = env['TMP'] = str(temporary)
    started = []
    children = []
    try:
        for name, (command, directory) in definitions.items():
            with (LOGS / (name + '.out.log')).open('wb') as stdout, (LOGS / (name + '.err.log')).open('wb') as stderr:
                child = subprocess.Popen(command, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
            children.append(child)
            info = identity(child.pid)
            if info is None:
                raise RuntimeError('Service exited: ' + name)
            started.append({'Name': name, 'ProcessId': child.pid, 'StartedUtcTicks': info[0]})
            atomic_json(STATE,started)
        deadline = time.monotonic() + 90
        last_error = ''
        while time.monotonic() < deadline:
            if any(child.poll() is not None for child in children):
                raise RuntimeError('A service exited. See logs in ' + str(LOGS))
            ok,last_error=healthy()
            if ok:
                mark_runtime_ready(runtime,RUNTIME)
                return
            time.sleep(.5)
        raise RuntimeError('启动超时：'+last_error+'。请查看logs目录，或再次启动尝试恢复。')
    except BaseException:
        stop_services(started)
        STATE.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('start', 'stop', 'restart', 'status'))
    parser.add_argument('--no-browser', action='store_true')
    options = parser.parse_args()
    try:
        with operation_lock():
            if options.action=='status':sys.exit(0 if status() else 2)
            elif options.action=='restart':stop();start(options.no_browser)
            elif options.action=='start':start(options.no_browser)
            else:stop()
    except Exception as exception:
        print('Error: ' + str(exception), file=sys.stderr)
        sys.exit(1)
