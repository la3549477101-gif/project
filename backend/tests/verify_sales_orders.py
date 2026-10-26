"""Sales orders exercise real HTTP + disposable H2; no real customer data."""
import concurrent.futures
import csv
import io
import subprocess
import threading
import unittest
import urllib.request
import uuid
import verify_company_weekly as fixture


class SalesOrders(unittest.TestCase):
    @classmethod
    def setUpClass(cls): fixture.CompanyWorkflow.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls): fixture.CompanyWorkflow.tearDownClass.__func__(cls)

    def call(self, path, data=None, method=None, want=200):
        status, result = fixture.http(path, data, method)
        self.assertEqual(status, want, (path, result))
        return result

    def setup_order(self):
        customer = self.call('/customers', {'fullName':'合成订单客户-'+uuid.uuid4().hex, 'profile':{'paymentCondition':'月结30天','invoiceDate':'次月5日前'}}, want=201)
        project = self.call('/projects', {'projectName':'合成订单项目','customerId':customer['id'],'stage':'EVT'}, want=201)
        a = self.call(f"/projects/{project['id']}/details", {'materialModel':'MODEL-A','specification':'SPEC-A','quantityUnit':'件','quotePrice':'99','businessStage':'样品送测'}, want=201)
        b = self.call(f"/projects/{project['id']}/details", {'materialModel':'MODEL-B','specification':'SPEC-B','quantityUnit':'件'}, want=201)
        body = {'requestKey':str(uuid.uuid4()),'customerId':customer['id'],'customerOrderNo':'','orderDate':'2026-10-26','purpose':'SAMPLE','currency':'CNY','source':'合成客户采购确认','notes':'',
                'lines':[{'detailId':a['id'],'quantity':'3','unit':'件','unitPrice':'0.335'}, {'detailId':b['id'],'quantity':'1','unit':'件','unitPrice':'0.005'}]}
        return customer, project, a, b, body

    def save(self, body):
        preview = self.call('/orders/preview', body)
        return self.call('/orders', {**body,'reviewHash':preview['reviewHash']}, want=201)

    def test_preview_zero_writes_line_rounding_and_customer_currency_totals(self):
        c,p,a,b,body = self.setup_order()
        before = self.call(f"/activities?scope=all&customerId={c['id']}")['total']
        preview = self.call('/orders/preview', body)
        self.assertEqual([row['amount'] for row in preview['lines']], ['1.01','0.01'])
        self.assertEqual(preview['totalAmount'], '1.02')
        self.assertEqual(self.call(f"/orders?customerId={c['id']}")['total'], 0)
        self.assertEqual(self.call(f"/activities?scope=all&customerId={c['id']}")['total'], before)
        first = self.save(body)
        self.assertEqual(first['totalAmount'], '1.02')
        self.assertTrue(first['internalNumber'])
        self.save({**body,'requestKey':str(uuid.uuid4()),'purpose':'MASS_PRODUCTION'})
        self.save({**body,'requestKey':str(uuid.uuid4()),'currency':'USD'})
        listing = self.call(f"/orders?customerId={c['id']}&size=1")
        self.assertEqual(listing['total'], 3)
        self.assertEqual(len(listing['items']), 1)
        totals = {t['currency']:(t['amount'],t['orderCount']) for t in listing['totals']}
        self.assertEqual(totals, {'CNY':('2.04',2),'USD':('1.02',1)})
        self.assertEqual(self.call(f"/projects/{p['id']}/details")[0]['businessStage'], '样品送测')

    def test_retry_same_key_returns_original_but_changed_content_is_conflict(self):
        c,p,a,b,body = self.setup_order()
        preview = self.call('/orders/preview', body)
        confirmed = {**body,'reviewHash':preview['reviewHash']}
        first = self.call('/orders', confirmed, want=201)
        again = self.call('/orders', confirmed, want=201)
        self.assertEqual(again['id'], first['id'])
        self.call('/orders', {**confirmed,'notes':'改变内容'}, want=409)
        self.assertEqual(self.call(f"/orders?customerId={c['id']}")['total'], 1)

    def test_customer_terms_and_model_names_are_immutable_order_snapshots(self):
        c,p,a,b,body = self.setup_order()
        first = self.save(body)
        self.call(f"/customers/{c['id']}", {**c,'fullName':c['fullName']+'改名','profile':{'paymentCondition':'预付款'}}, 'PUT')
        self.call(f"/projects/{p['id']}/details/{a['id']}", {**a,'materialModel':'MODEL-CHANGED'}, 'PUT')
        old = self.call(f"/orders/{first['id']}")
        self.assertEqual(old['customerName'], c['fullName'])
        self.assertEqual(old['termsSnapshot']['paymentCondition'], '月结30天')
        self.assertEqual(old['lines'][0]['materialModel'], 'MODEL-A')
        second = self.save({**body,'requestKey':str(uuid.uuid4())})
        self.assertEqual(second['termsSnapshot']['paymentCondition'], '预付款')
        self.assertEqual(second['lines'][0]['materialModel'], 'MODEL-CHANGED')

    def test_changed_customer_data_invalidates_preview_without_creating_order(self):
        c,p,a,b,body = self.setup_order()
        preview = self.call('/orders/preview', body)
        self.call(f"/customers/{c['id']}", {**c,'profile':{'paymentCondition':'预付款'}}, 'PUT')
        self.call('/orders', {**body,'reviewHash':preview['reviewHash']}, want=409)
        self.assertEqual(self.call(f"/orders?customerId={c['id']}")['total'], 0)

    def test_invalid_lines_dates_currency_and_foreign_or_archived_models_do_not_save(self):
        c,p,a,b,body = self.setup_order()
        other = self.call('/projects', {'projectName':'另一客户项目'}, want=201)
        wrong = self.call(f"/projects/{other['id']}/details", {'materialModel':'FOREIGN'}, want=201)
        for patch in [{'lines':[]},{'orderDate':'0000-01-01'},{'currency':''},{'purpose':'INTENTION'},
                      {'lines':[{**body['lines'][0],'quantity':'0'}]}, {'lines':[{**body['lines'][0],'unitPrice':'0.0000001'}]},
                      {'lines':[{**body['lines'][0],'detailId':wrong['id']}]}, {'source':''}]:
            with self.subTest(patch=next(iter(patch))):
                self.call('/orders/preview', {**body,**patch}, want=400)
        self.call(f"/projects/{p['id']}/details/{a['id']}/archive", {'archived':True})
        self.call('/orders/preview', body, want=409)
        self.assertEqual(self.call(f"/orders?customerId={c['id']}")['total'], 0)
        self.call('/orders', {**body,'reviewHash':'fake'}, want=409)

    def test_duplicate_customer_order_number_and_repeated_detail_are_rejected(self):
        c,p,a,b,body = self.setup_order()
        self.save({**body,'customerOrderNo':'PO-001'})
        self.call('/orders/preview', {**body,'requestKey':str(uuid.uuid4()),'customerOrderNo':' po-001 '}, want=409)
        self.call('/orders/preview', {**body,'lines':[body['lines'][0],body['lines'][0]]}, want=400)

    def test_simultaneous_retry_creates_one_order_and_one_audit(self):
        c,p,a,b,body = self.setup_order()
        preview = self.call('/orders/preview', body)
        payload = {**body,'reviewHash':preview['reviewHash']}
        barrier = threading.Barrier(2)
        def create(_):
            barrier.wait(timeout=5)
            return fixture.http('/orders', payload)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(create, range(2)))
        self.assertEqual([status for status,_ in rows], [201,201], rows)
        self.assertEqual(rows[0][1]['id'], rows[1][1]['id'])
        self.assertEqual(self.call(f"/orders?customerId={c['id']}")['total'], 1)
        events = self.call(f"/activities?scope=all&customerId={c['id']}")['items']
        self.assertEqual(len([e for e in events if e['entityType']=='ORDER']), 1)

    def test_csv_snapshot_export_escapes_formula_and_matches_selected_customer(self):
        c,p,a,b,body = self.setup_order()
        order = self.save({**body,'customerOrderNo':'=1+2'})
        with urllib.request.urlopen(fixture.BASE+f"/orders/export?customerId={c['id']}") as response:
            content = response.read().decode('utf-8-sig')
        rows = list(csv.DictReader(io.StringIO(content)))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['客户订单号'], "'=1+2")
        self.assertEqual(rows[0]['订单含税总额'], '1.02')
        self.assertEqual(rows[0]['内部订单号'], order['internalNumber'])
        self.assertEqual(rows[1]['材料型号'], 'MODEL-B')
        self.assertEqual(rows[1]['订单含税总额'], '', 'Order total is exported once, so summing the column cannot double-count a multi-line order')

    def test_second_project_and_changed_model_preview_cannot_create_wrong_order(self):
        c,p,a,b,body = self.setup_order()
        other = self.call('/projects', {'projectName':'客户另一个项目','customerId':c['id']}, want=201)
        d = self.call(f"/projects/{other['id']}/details", {'materialModel':'SECOND-PROJECT'}, want=201)
        self.call('/orders/preview', {**body,'lines':[body['lines'][0],{**body['lines'][1],'detailId':d['id']}]}, want=400)
        preview = self.call('/orders/preview', body)
        self.call(f"/projects/{p['id']}/details/{a['id']}", {**a,'specification':'CHANGED-SPEC'}, 'PUT')
        self.call('/orders', {**body,'reviewHash':preview['reviewHash']}, want=409)
        self.assertEqual(self.call(f"/orders?customerId={c['id']}")['total'], 0)

    def test_amount_strings_preserve_maximum_precision_and_server_ignores_fake_total(self):
        c,p,a,b,body = self.setup_order()
        line = {**body['lines'][0],'quantity':'1.000001','unitPrice':'9999999999999.123456'}
        preview = self.call('/orders/preview', {**body,'lines':[line]})
        self.assertEqual(preview['totalAmount'], '10000009999999.12')
        saved = self.call('/orders', {**body,'lines':[line],'reviewHash':preview['reviewHash'],'totalAmount':'0.01'}, want=201)
        self.assertEqual(saved['totalAmount'], '10000009999999.12')
        self.assertIsInstance(saved['totalAmount'], str)
        self.assertEqual(self.call(f"/orders/{saved['id']}")['lines'][0]['unitPrice'], '9999999999999.123456')

    def test_z_restart_keeps_order_lines_terms_and_totals(self):
        c,p,a,b,body = self.setup_order()
        saved = self.save(body)
        cls = type(self); command = cls.process.args
        cls.process.terminate(); cls.process.wait(timeout=15)
        cls.log.seek(0); cls.log.truncate()
        cls.process = subprocess.Popen(command, stdout=cls.log, stderr=cls.log, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        fixture.CompanyWorkflow.wait_ready.__func__(cls)
        actual = self.call(f"/orders/{saved['id']}")
        self.assertEqual(actual['lines'], saved['lines'])
        self.assertEqual(actual['termsSnapshot'], saved['termsSnapshot'])
        self.assertEqual(actual['totalAmount'], '1.02')


if __name__ == '__main__': unittest.main(argv=['verify_sales_orders'] + fixture.rest)
