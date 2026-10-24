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

APP = Path(__file__).resolve().parent
TOOLS = APP.parents[2] / '.tools'
LOGS = APP / 'logs'
STATE = LOGS / 'services.json'
URL = 'http://127.0.0.1:5173/'
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


def specs():
    java = TOOLS / 'jdk-21.0.12.1+1/bin/java.exe'
    node = TOOLS / 'node-v24.22.1-win-x64/node.exe'
    python = APP / 'backend/flask/.venv/Scripts/python.exe'
    return {
        'springboot': ([str(java), '-jar', str(APP / 'backend/springboot/target/odm-tracker-1.0.0.jar')], APP / 'backend/springboot'),
        'flask': ([str(python), '-m', 'flask', '--app', 'app', 'run', '--host', '127.0.0.1', '--port', '5000'], APP / 'backend/flask'),
        'frontend': ([str(node), str(APP / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--strictPort'], APP / 'frontend'),
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
    if not expected or current != (str(service['StartedUtcTicks']), os.path.normcase(os.path.abspath(expected[0][0]))):
        raise RuntimeError('Process identity changed; refusing to stop an unrelated process.')
    return True


def read_state():
    if not STATE.exists():
        return []
    raw = STATE.read_bytes()
    text = raw.decode('utf-16') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8-sig')
    data = json.loads(text)
    return data if isinstance(data, list) else [data]


def stop_services(services):
    for service in services:
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
    print('Services stopped. Project data retained.')


def start(no_browser):
    LOGS.mkdir(exist_ok=True)
    old = read_state()
    if old:
        active = [matches(service) for service in old]
        if any(active):
            if all(active):
                with HTTP.open('http://127.0.0.1:8080/api/health', timeout=5) as response:
                    if not json.load(response).get('databaseWritable'):
                        raise RuntimeError('Database is not writable. Check the data directory permissions.')
                print('Already running: ' + URL)
                if not no_browser:
                    webbrowser.open(URL)
                return
            raise RuntimeError('Some services are still running. Run stop-app.cmd first.')
        STATE.unlink()
    for port in (8080, 5000, 5173):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    definitions = specs()
    for command, _ in definitions.values():
        if not Path(command[0]).is_file():
            raise RuntimeError('Missing runtime: ' + command[0])
    for required in (APP / 'backend/springboot/target/odm-tracker-1.0.0.jar', APP / 'frontend/node_modules/vite/bin/vite.js'):
        if not required.is_file():
            raise RuntimeError('Missing build or dependencies: ' + str(required))
    env = dict(os.environ)
    env['PATH'] = os.pathsep.join([str(Path(definitions[name][0][0]).parent) for name in ('frontend', 'springboot', 'flask')] + [env.get('PATH', '')])
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
            STATE.write_text(json.dumps(started, indent=2), encoding='utf-8')
        deadline = time.monotonic() + 90
        last_error = ''
        while time.monotonic() < deadline:
            if any(child.poll() is not None for child in children):
                raise RuntimeError('A service exited. See logs in ' + str(LOGS))
            try:
                for url in ('http://127.0.0.1:8080/api/health', 'http://127.0.0.1:5000/api/summary', URL):
                    with HTTP.open(url, timeout=10) as response:
                        if url.endswith('/health') and not json.load(response).get('databaseWritable'):
                            raise RuntimeError('Database is not writable.')
                        response.read()
                print('Ready: ' + URL)
                if not no_browser:
                    webbrowser.open(URL)
                return
            except urllib.error.HTTPError as exception:
                if exception.code == 503 and exception.url.endswith('/health'):
                    message = json.loads(exception.read().decode('utf-8')).get('message', 'Database unavailable.')
                    raise RuntimeError(message) from exception
                last_error = str(exception)
                time.sleep(.5)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exception:
                last_error = str(exception)
                time.sleep(.5)
        raise RuntimeError('Startup timed out: ' + last_error)
    except BaseException:
        stop_services(started)
        STATE.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('start', 'stop'))
    parser.add_argument('--no-browser', action='store_true')
    options = parser.parse_args()
    try:
        start(options.no_browser) if options.action == 'start' else stop()
    except Exception as exception:
        print('Error: ' + str(exception), file=sys.stderr)
        sys.exit(1)
