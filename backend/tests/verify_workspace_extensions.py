"""Regression checks for customer filing, specifications and history on disposable H2."""
import concurrent.futures
import http.server
import decimal
import subprocess
import threading
import time
import unittest
import uuid
import verify_company_weekly as fixture


class FixtureIsolation(unittest.TestCase):
    def test_fixture_does_not_accept_another_servers_health_response(self):
        class Probe(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.server.probe_requests += 1
                self.send_response(200); self.end_headers()
                self.wfile.write(b'{"databaseWritable": true}')
            def log_message(self, *args):
                pass
        class Temporary:
            pass
        probe = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Probe)
        probe.probe_requests = 0
        thread = threading.Thread(target=probe.serve_forever, daemon=True)
        thread.start()
        previous = fixture.BASE
        fixture.BASE = f'http://127.0.0.1:{probe.server_port}/api'
        started = False
        try:
            fixture.CompanyWorkflow.setUpClass.__func__(Temporary)
            started = True
            self.assertEqual(probe.probe_requests, 0, 'A healthy unrelated server must not be used as the test database')
        finally:
            if started:
                fixture.CompanyWorkflow.tearDownClass.__func__(Temporary)
            fixture.BASE = previous
            probe.shutdown(); probe.server_close(); thread.join(timeout=5)


class WorkspaceExtensions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.CompanyWorkflow.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        fixture.CompanyWorkflow.tearDownClass.__func__(cls)

    def call(self, path, data=None, method=None, want=200):
        status, result = fixture.http(path, data, method)
        self.assertEqual(status, want, (path, result))
        return result

    def customer(self, **values):
        return self.call('/customers', {'fullName': '合成检查客户-' + uuid.uuid4().hex, **values}, want=201)

    def project(self, **values):
        return self.call('/projects', {'projectName': '合成检查项目', **values}, want=201)

    def detail(self, project, **values):
        return self.call(f"/projects/{project['id']}/details", {'materialModel': 'MODEL-A', 'specification': '10 x 20 mm', **values}, want=201)

    def history(self, project):
        return self.call(f"/projects/{project['id']}/followups")

    def test_profile_preserves_omitted_values_merges_and_clears_explicit_blanks(self):
        customer = self.customer(profile={'paymentCondition': '月结30天', 'taxIncluded': '是', 'creditLimit': '人民币10万元'})
        path = f"/customers/{customer['id']}"
        before = self.call(f"/activities?scope=all&customerId={customer['id']}")['total']
        body = {'fullName': customer['fullName']}
        unchanged = self.call(path, body, 'PUT')
        self.assertEqual(unchanged['profile']['paymentCondition'], '月结30天')
        self.assertEqual(self.call(f"/activities?scope=all&customerId={customer['id']}")['total'], before)
        changed = self.call(path, {**body, 'profile': {'invoiceDate': '次月5日前'}}, 'PUT')
        self.assertEqual(changed['profile']['creditLimit'], '人民币10万元')
        self.assertEqual(changed['profile']['invoiceDate'], '次月5日前')
        cleared = self.call(path, {**body, 'profile': {'taxIncluded': '', 'creditLimit': None}}, 'PUT')
        self.assertNotIn('taxIncluded', cleared['profile'])
        self.assertNotIn('creditLimit', cleared['profile'])
        self.assertEqual(cleared['profile']['paymentCondition'], '月结30天')

    def test_profile_bad_field_options_length_and_calendar_dates_rollback(self):
        customer = self.customer(profile={'industry': '热管理'})
        for profile in [{'unknownField': 'x'}, {'paymentCondition': '错误选项'}, {'taxIncluded': '未知'},
                        {'address': 'x' * 2001}, {'filingDate': '2026-02-30'}, {'approvalDate': '0000-01-01'}]:
            with self.subTest(profile=next(iter(profile))):
                self.call(f"/customers/{customer['id']}", {'fullName': customer['fullName'], 'profile': profile}, 'PUT', want=400)
                self.assertEqual(self.call(f"/customers/{customer['id']}")['profile'], {'industry': '热管理'})

    def test_maximum_length_names_and_text_are_saved_with_audit_history(self):
        project = self.project(projectName='项' * 255)
        detail = self.detail(project, materialModel='型' * 255, specification='规' * 255, statusNote='况' * 2000, notes='备' * 2000)
        self.assertEqual(len(detail['materialModel']), 255)
        self.assertGreater(len(self.history(project)['items'][0]['content']), 4000)
        self.assertIn('型' * 255, self.call('/activities?scope=all')['items'][0]['objectName'])

    def test_decimal_precision_blank_and_noop_save_dont_create_fake_history(self):
        project = self.project(stage='EVT')
        detail = self.detail(project, quotePrice='9999999999999.123456', estimatedAnnualQuantity='0', expectedMpText='2027年Q1')
        rows = self.call(f"/projects/{project['id']}/details")
        self.assertIsInstance(rows[0]['quotePrice'], str)
        self.assertEqual(decimal.Decimal(rows[0]['quotePrice']), decimal.Decimal('9999999999999.123456'))
        self.assertIsNone(rows[0]['competitorPrice'])
        self.assertEqual(rows[0]['expectedMpText'], '2027年Q1')
        count = self.history(project)['total']
        self.call(f"/projects/{project['id']}/details/{detail['id']}", rows[0], 'PUT')
        self.assertEqual(self.history(project)['total'], count)
        for value in ['-1', '0.0000001', '10000000000000']:
            with self.subTest(value=value):
                self.call(f"/projects/{project['id']}/details/{detail['id']}", {**rows[0], 'quotePrice': value}, 'PUT', want=400)
                self.assertEqual(self.history(project)['total'], count)
        actual = self.call(f"/projects/{project['id']}/details")[0]
        self.assertEqual(actual['quotePrice'], rows[0]['quotePrice'])
        self.assertEqual(self.call('/projects?stage=EVT')[-1]['stage'], 'EVT')

    def test_foreign_project_and_archived_details_are_not_editable(self):
        project = self.project()
        other = self.project()
        detail = self.detail(project)
        body = {'detailId': detail['id'], 'contactDate': '2026-10-26', 'content': '客户反馈', 'source': '合成沟通'}
        self.call(f"/projects/{other['id']}/followups", body, want=400)
        self.call(f"/projects/{other['id']}/details/{detail['id']}", detail, 'PUT', want=400)
        self.call(f"/projects/{project['id']}/details/{detail['id']}/archive", {'archived': True})
        self.call(f"/projects/{project['id']}/followups", body, want=409)
        self.call(f"/projects/{project['id']}/details/{detail['id']}", detail, 'PUT', want=409)
        self.detail_duplicate(project, detail)
        restored = self.call(f"/projects/{project['id']}/details/{detail['id']}/archive", {'archived': False})
        self.assertFalse(restored['archived'])
        self.assertEqual(self.history(project)['total'], 3)

    def detail_duplicate(self, project, detail):
        self.call(f"/projects/{project['id']}/details", {'materialModel': detail['materialModel'].lower(), 'specification': detail['specification']}, want=409)

    def test_followup_keeps_stage_before_and_after_and_snapshot_after_rename(self):
        project = self.project(stage='DVT')
        detail = self.detail(project, businessStage='报价中')
        row = self.call(f"/projects/{project['id']}/followups", {'detailId': detail['id'], 'contactDate': '2026-10-20', 'content': '已安排送样', 'source': '合成邮件', 'newBusinessStage': '样品送测', 'recordedAt': '2000-01-01T00:00:00Z'}, want=201)
        self.assertEqual((row['previousBusinessStage'], row['businessStage']), ('报价中', '样品送测'))
        self.assertNotEqual(row['recordedAt'], '2000-01-01T00:00:00Z')
        current = self.call(f"/projects/{project['id']}/details")[0]
        self.call(f"/projects/{project['id']}/details/{detail['id']}", {**current, 'materialModel': 'MODEL-RENAMED'}, 'PUT')
        old = [item for item in self.history(project)['items'] if item['id'] == row['id']][0]
        self.assertEqual(old['materialModel'], 'MODEL-A')
        self.assertEqual(old['businessStage'], '样品送测')
        self.assertEqual([p for p in self.call('/projects') if p['id'] == project['id']][0]['stage'], 'DVT')

    def test_followup_validation_rolls_back_stage_and_never_invents_project_stage(self):
        project = self.project()
        detail = self.detail(project, businessStage='报价中')
        count = self.history(project)['total']
        base = {'detailId': detail['id'], 'contactDate': '2026-10-26', 'content': '合成反馈', 'source': '合成来源', 'newBusinessStage': '样品送测'}
        for patch in [{'nextAction': 'x' * 2001}, {'source': ''}, {'contactDate': '2026-02-30'}, {'detailId': None}]:
            with self.subTest(patch=next(iter(patch))):
                self.call(f"/projects/{project['id']}/followups", {**base, **patch}, want=400)
                self.assertEqual(self.call(f"/projects/{project['id']}/details")[0]['businessStage'], '报价中')
                self.assertEqual(self.history(project)['total'], count)

    def test_protected_project_rejects_whole_bulk_delete_but_empty_project_deletes(self):
        project = self.project()
        empty = self.project()
        self.detail(project)
        self.call(f"/projects/{project['id']}", method='DELETE', want=409)
        self.call('/projects/bulk-delete', [empty['id'], project['id']], want=409)
        ids = {p['id'] for p in self.call('/projects')}
        self.assertIn(empty['id'], ids)
        self.assertIn(project['id'], ids)
        self.call(f"/projects/{empty['id']}", method='DELETE', want=204)

    def test_history_pagination_and_missing_project_are_rejected(self):
        project = self.project()
        self.call(f"/projects/{project['id']}/followups?page=-1", want=400)
        self.call(f"/projects/{project['id']}/followups?size=101", want=400)
        self.call('/projects/999999/details', want=404)
        self.call('/projects/999999/followups', want=404)

    def test_priority_is_independent_and_old_project_forms_cannot_clear_it(self):
        customer = self.customer()
        project = self.project(customerId=customer['id'], stage='EVT')
        other = self.project(customerId=customer['id'])
        endpoint = f"/projects/{project['id']}/priority"
        before = self.call(f"/activities?scope=all&customerId={customer['id']}")['total']
        flagged = self.call(endpoint, {'important': True})
        self.assertTrue(flagged['important'])
        self.call(endpoint, {'important': True})
        self.assertEqual(self.call(f"/activities?scope=all&customerId={customer['id']}")['total'], before + 1)
        rows = self.call(f"/projects?customerId={customer['id']}&important=true")
        self.assertEqual([r['id'] for r in rows], [project['id']])
        self.assertEqual(len(self.call(f"/projects?customerId={customer['id']}")), 2)
        unchanged = self.call(f"/projects/{project['id']}", project, 'PUT')
        self.assertTrue(unchanged['important'])
        self.assertEqual(unchanged['stage'], 'EVT')
        self.call(endpoint, {}, want=400)
        cleared = self.call(endpoint, {'important': False})
        self.assertFalse(cleared['important'])
        self.assertEqual(self.call(f"/projects?customerId={customer['id']}&important=true"), [])
        self.assertEqual(self.call(f"/activities?scope=all&customerId={customer['id']}")['total'], before + 2)

    def parallel(self, *actions):
        barrier = threading.Barrier(len(actions))
        def run(action):
            barrier.wait(timeout=5)
            return action()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_concurrent_duplicate_specification_creates_only_one_record(self):
        project = self.project()
        path = f"/projects/{project['id']}/details"
        body = {'materialModel': 'MODEL-ONE', 'specification': 'SPEC-ONE'}
        results = self.parallel(lambda: fixture.http(path, body), lambda: fixture.http(path, body))
        self.assertEqual(sorted(status for status, _ in results), [201, 409])
        self.assertEqual(len(self.call(path)), 1)
        self.assertEqual(self.history(project)['total'], 1)

    def test_concurrent_add_and_delete_cannot_orphan_child_history(self):
        for _ in range(4):
            project = self.project()
            prefix = f"/projects/{project['id']}"
            results = self.parallel(lambda: fixture.http(prefix + '/details', {'materialModel': 'MODEL-RACE'}), lambda: fixture.http(prefix, method='DELETE'))
            created, deleted = (item[0] for item in results)
            self.assertIn((created, deleted), [(201, 409), (404, 204)])
            if created == 201:
                self.assertEqual(len(self.call(prefix + '/details')), 1)

    def test_z_restart_preserves_customer_details_and_history(self):
        customer = self.customer(profile={'paymentCondition': '预付款', 'invoiceDate': '次月开票'})
        project = self.project(customerId=customer['id'])
        detail = self.detail(project, quotePrice='0.123456')
        before = self.history(project)
        cls = type(self)
        command = cls.process.args
        cls.process.terminate(); cls.process.wait(timeout=15)
        cls.log.seek(0); cls.log.truncate()
        cls.process = subprocess.Popen(command, stdout=cls.log, stderr=cls.log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        fixture.CompanyWorkflow.wait_ready.__func__(cls)
        self.assertEqual(self.call(f"/customers/{customer['id']}")['profile'], customer['profile'])
        stored = self.call(f"/projects/{project['id']}/details")[0]
        self.assertEqual(stored['id'], detail['id'])
        self.assertEqual(decimal.Decimal(stored['quotePrice']), decimal.Decimal('0.123456'))
        self.assertEqual(self.history(project), before)


if __name__ == '__main__':
    unittest.main(argv=['verify_workspace_extensions'] + fixture.rest)
