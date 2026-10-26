"""Run all three services on separate ports, using only synthetic fixtures."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))
import manage

STATE = APP / 'work/company-weekly-preview.json'
BASE = 'http://127.0.0.1:18083/api'
processes = []


def call(path, body=None, method=None, base=BASE):
    request = urllib.request.Request(base + path, None if body is None else json.dumps(body).encode(),
                                     {'Content-Type': 'application/json'}, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def wait(url):
    for _ in range(120):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(.2)
    raise RuntimeError('Preview service not ready: ' + url)


def start(args):
    if STATE.exists():
        raise RuntimeError('Existing preview state found; stop it first')
    root = Path(tempfile.mkdtemp(prefix='company-preview-', dir=APP / 'work')).resolve()
    desktop = root / 'Desktop'
    desktop.mkdir()
    env = os.environ.copy()
    env.update(SPRING_API=BASE, ODM_DESKTOP_ROOT=str(desktop), ODM_FRONTEND_ORIGIN='http://127.0.0.1:15173',
               VITE_SPRING_API=BASE, VITE_FLASK_API='http://127.0.0.1:15003/api')

    def spawn(command, cwd, name):
        with (root / (name + '.log')).open('w', encoding='utf-8') as log:
            child = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=log,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        processes.append(child)
        return child

    def java(jar, name):
        return spawn([args.java, '-jar', str(jar), '--server.port=18083',
            '--spring.datasource.url=jdbc:h2:file:' + (root / 'ledger').as_posix() + ';WRITE_DELAY=0',
            '--odm.flask-api=http://127.0.0.1:15003/api', '--odm.extra-origin=http://127.0.0.1:15173'],
            APP / 'backend/springboot', name)

    try:
        # Create a true pre-upgrade database to prove legacy records get no invented audit time.
        legacy = java(APP / 'work/company-weekly/baseline.jar', 'legacy')
        wait(BASE + '/health')
        old = call('/projects', {'projectName': '旧项目迁移示例', 'terminalCustomer': '示例终端'})
        assert len(call('/projects')) == 1
        legacy.terminate(); legacy.wait(timeout=15); processes.remove(legacy)
        java(APP / 'backend/springboot/target/odm-tracker-1.0.0.jar', 'spring')
        spawn([sys.executable, '-m', 'flask', '--app', 'app', 'run', '--host', '127.0.0.1', '--port', '15003'], APP / 'backend/flask', 'flask')
        wait(BASE + '/health'); wait('http://127.0.0.1:15003/api/summary')
        assert call('/activities')['total'] == 0
        migrated = call('/projects')[0]
        assert migrated.get('createdAt') is None and migrated.get('customerId') is None
        a = call('/customers', {'fullName': '示例客户甲', 'shortName': '客户甲', 'contactName': '演示联系人'})
        b = call('/customers', {'fullName': '示例客户乙', 'shortName': '客户乙'})
        assert a['folderStatus'] == b['folderStatus'] == 'READY', (a, b)
        assert Path(a['archivePath']).parent == desktop
        call('/projects/assign', {'ids': [old['id']], 'customerId': a['id']})
        p = call('/projects', {'projectName': '液冷产品验证项目', 'customerId': a['id'], 'terminalCustomer': '示例终端', 'stage': 'EVT', 'estimatedTotalDemand': 1000})
        p['estimatedTotalDemand'] = 1500
        call('/projects/' + str(p['id']), p, 'PUT')
        call('/projects', {'projectName': '机柜散热项目', 'customerId': b['id'], 'application': '热管理'})
        call('/projects', {'projectName': '待确认客户归属项目'})
        batch = {'projects': [{'projectName': '导入客户甲示例项目', 'customerId': a['id']}]}
        first = call('/import/confirm', batch, base='http://127.0.0.1:15003/api')
        assert first['importedCount'] == 1
        total = call('/activities')['total']
        again = call('/import/confirm', batch, base='http://127.0.0.1:15003/api')
        assert again['skippedCount'] == 1 and call('/activities')['total'] == total
        no_op = call('/projects/' + str(p['id']), call('/projects?customerId=' + str(a['id']))[1], 'PUT')
        assert call('/activities')['total'] == total
        renamed = dict(a, fullName='示例客户甲有限公司')
        renamed = call('/customers/' + str(a['id']), renamed, 'PUT')
        assert renamed['archivePath'] == a['archivePath']
        assert call('/customers/' + str(a['id']) + '/folder/retry', {}, 'POST')['folderStatus'] == 'READY'
        total = call('/activities')['total']
        current = processes[0]
        current.terminate(); current.wait(timeout=15); processes.remove(current)
        java(APP / 'backend/springboot/target/odm-tracker-1.0.0.jar', 'spring-restart')
        wait(BASE + '/health')
        assert call('/activities')['total'] == total
        spawn([args.node, str(APP / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '15173', '--strictPort'], APP / 'frontend', 'frontend')
        wait('http://127.0.0.1:15173')
        state = {'root': str(root), 'processes': [{'pid': p.pid, 'identity': list(manage.identity(p.pid))} for p in processes], 'url': 'http://127.0.0.1:15173',
                 'checks': ['legacy migration without fake timestamps', 'real temporary desktop folders', 'company assignment', 'project change history', 'import duplicate has no event', 'no-op has no event', 'rename keeps folder', 'restart preserves history']}
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'url': state['url'], 'checks': state['checks']}, ensure_ascii=False))
    except BaseException:
        for p in processes:
            if p.poll() is None:
                p.terminate(); p.wait(timeout=15)
        print('Preview logs: ' + str(root), file=sys.stderr)
        raise


def stop():
    if not STATE.exists():
        return
    state = json.loads(STATE.read_text(encoding='utf-8'))
    for p in state['processes']:
        identity = manage.identity(p['pid'])
        if identity and list(identity) == p['identity']:
            subprocess.run(['taskkill', '/PID', str(p['pid']), '/T', '/F'], capture_output=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
    STATE.unlink()
    print('Isolated preview stopped; logs and test database retained under work/')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop'])
    parser.add_argument('--java')
    parser.add_argument('--node')
    args = parser.parse_args()
    start(args) if args.action == 'start' else stop()
