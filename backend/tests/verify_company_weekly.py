"""HTTP acceptance against a disposable H2 database, never the real ledger."""
import argparse
import datetime as dt
import json
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--java', required=True)
parser.add_argument('--jar', required=True)
args, rest = parser.parse_known_args()
BASE = 'http://127.0.0.1:18083/api'


def http(path, body=None, method=None):
    req = urllib.request.Request(BASE + path, None if body is None else json.dumps(body).encode(),
                                 {'Content-Type': 'application/json'}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


class CompanyWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='odm-company-test-')
        root = Path(cls.temp.name)
        cls.log = (root / 'server.log').open('w', encoding='utf-8')
        cls.process = subprocess.Popen([args.java, '-jar', args.jar, '--server.port=18083',
            '--spring.datasource.url=jdbc:h2:file:' + (root / 'ledger').as_posix() + ';WRITE_DELAY=0',
            '--odm.flask-api=http://127.0.0.1:9/api'], stdout=cls.log, stderr=cls.log,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for _ in range(100):
            try:
                if http('/health')[0] == 200:
                    return
            except OSError:
                pass
            if cls.process.poll() is not None:
                break
            time.sleep(.2)
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.log.close()
        raise RuntimeError((root / 'server.log').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=15)
        cls.log.close()
        cls.temp.cleanup()

    def test_company_and_change_workflow(self):
        status, a = http('/customers', {'fullName': '合成客户甲', 'shortName': '甲', 'archivePath': 'C:/fake'})
        self.assertEqual(status, 201, a)
        self.assertNotEqual(a.get('archivePath'), 'C:/fake')
        self.assertEqual(a['folderStatus'], 'FAILED')
        self.assertEqual(http('/customers', {'fullName': '  合成客户甲  '})[0], 409)
        _, b = http('/customers', {'fullName': '合成客户乙'})
        status, p = http('/projects', {'projectName': '合成项目', 'terminalCustomer': '合成终端',
            'customerId': a['id'], 'updatedAt': '2000-01-01T00:00:00Z'})
        self.assertEqual(status, 201, p)
        self.assertEqual(p['customerName'], '合成客户甲')
        self.assertNotEqual(p['updatedAt'], '2000-01-01T00:00:00Z')
        self.assertEqual(http('/projects?customerId=' + str(a['id']))[1][0]['id'], p['id'])
        self.assertEqual(http('/projects?customerId=' + str(b['id']))[1], [])
        self.assertEqual(http('/projects?unassigned=true')[1], [])
        _, before = http('/activities')
        self.assertEqual(before['total'], 3)
        self.assertEqual(http('/projects/' + str(p['id']), p, 'PUT')[0], 200)
        self.assertEqual(http('/activities')[1]['total'], before['total'])
        browser_form = dict(p)
        for field in ('terminalCustomer', 'odmIntegrator', 'moduleFactory', 'application', 'stage'):
            browser_form[field] = browser_form.get(field) or ''
        self.assertEqual(http('/projects/' + str(p['id']), browser_form, 'PUT')[0], 200)
        self.assertEqual(http('/activities')[1]['total'], before['total'], 'Empty form fields must not create fake updates')
        p['estimatedTotalDemand'] = 25
        _, p = http('/projects/' + str(p['id']), p, 'PUT')
        changes = http('/activities')[1]
        self.assertEqual(changes['total'], 4)
        self.assertIn('25', changes['items'][0]['detail'])
        status, _ = http('/projects/assign', {'ids': [p['id'], 999999], 'customerId': b['id']})
        self.assertEqual(status, 404)
        self.assertEqual(http('/projects?customerId=' + str(a['id']))[1][0]['id'], p['id'])
        status, _ = http('/projects/assign', {'ids': [p['id']], 'customerId': b['id']})
        self.assertEqual(status, 200)
        moved = http('/activities?customerId=' + str(a['id']))[1]['items'][0]
        self.assertEqual(moved['previousCustomerId'], a['id'])
        self.assertEqual(moved['customerId'], b['id'])
        self.assertEqual(moved['customerName'], '合成客户乙')
        self.assertEqual(http('/projects', {'projectName': '错误客户', 'customerId': 99999})[0], 400)
        _, free = http('/projects', {'projectName': '未归属合成项目'})
        self.assertEqual(http('/projects?unassigned=true')[1][0]['id'], free['id'])
        b['fullName'] = '合成客户乙改名'
        self.assertEqual(http('/customers/' + str(b['id']), b, 'PUT')[0], 200)
        self.assertEqual(http('/projects?customerId=' + str(b['id']))[1][0]['customerName'], '合成客户乙改名')
        status, week = http('/activities?size=2')
        self.assertEqual(status, 200)
        self.assertEqual(len(week['items']), 2)
        start = dt.datetime.fromisoformat(week['from'].replace('Z', '+00:00'))
        local = start.astimezone(dt.timezone(dt.timedelta(hours=8)))
        self.assertEqual((local.weekday(), local.hour), (0, 0))
        end = dt.datetime.fromisoformat(week['to'].replace('Z', '+00:00'))
        self.assertEqual(end - start, dt.timedelta(days=7))
        total = week['total']
        self.assertEqual(http('/activities?page=-1')[0], 400)
        self.assertEqual(http('/activities?size=10000')[0], 400)
        self.assertEqual(http('/activities?scope=unknown')[0], 400)
        self.assertEqual(http('/projects/' + str(p['id']), method='DELETE')[0], 204)
        self.assertEqual(http('/activities')[1]['total'], total)
        self.assertEqual(http('/customers/' + str(b['id']) + '/folder/retry', {}, 'POST')[0], 200)
        self.assertEqual(http('/activities')[1]['total'], total)


if __name__ == '__main__':
    unittest.main(argv=['verify_company_weekly'] + rest)
