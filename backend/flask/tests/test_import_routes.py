import csv
import io
import json
import unittest
from unittest.mock import patch

import app as service


HEADERS = ['终端客户', 'ODM集成商', '模组厂', '项目名称', '应用', '目前阶段', '测试阶段需求数量', '项目预计总需求量', '预计MP日期']


def project(name='路由验收项目', material=None):
    p = dict(terminalCustomer='', odmIntegrator='', moduleFactory='', projectName=name,
             application='', stage='', testDemandQuantity=None, estimatedTotalDemand=None, expectedMpDate=None)
    if material:
        p['reportData'] = json.dumps({'fields': {'材料型号': material, '客户': '示例客户'}, 'sheet': '开发', 'file': '示例.xls', 'row': 3}, ensure_ascii=False)
    return p


class ImportRoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = service.app.test_client()

    def test_preview_does_not_write_any_project(self):
        text = io.StringIO(); csv.writer(text).writerows([HEADERS, ['', '', '', '预览项目', '', '', '', '0', '']])
        with patch('requests.post', side_effect=AssertionError('预览不能写库')):
            r = self.client.post('/api/import/preview', data={'file': (io.BytesIO(text.getvalue().encode('utf-8')), '示例.csv')})
        self.assertEqual(200, r.status_code)
        self.assertEqual('预览项目', r.json['sheets'][0]['rows'][0]['project']['projectName'])
        self.assertEqual(0, r.json['sheets'][0]['rows'][0]['project']['estimatedTotalDemand'])

    def test_confirm_skips_exact_existing_and_in_batch_duplicates(self):
        p = project()
        with patch('app.fetch_projects', return_value=[dict(p, id=1)]), patch('requests.post', side_effect=AssertionError('重复不能写库')):
            r = self.client.post('/api/import/confirm', json={'projects': [p, p]})
        self.assertEqual(200, r.status_code)
        self.assertEqual({'importedCount': 0, 'skippedCount': 2}, r.json)

    def test_confirm_preserves_different_materials_in_one_project(self):
        saved = []
        def save(url, **kwargs):
            saved.extend(kwargs['json'])
            response = service.requests.Response(); response.status_code = 201; response._content = b'[]'
            return response
        with patch('app.fetch_projects', return_value=[]), patch('requests.post', side_effect=save):
            r = self.client.post('/api/import/confirm', json={'projects': [project(material='A'), project(material='B')]})
        self.assertEqual(200, r.status_code)
        self.assertEqual(2, r.json['importedCount'])
        self.assertEqual(['A', 'B'], [json.loads(p['reportData'])['fields']['材料型号'] for p in saved])

    def test_invalid_batch_is_rejected_before_any_write(self):
        with patch('requests.post', side_effect=AssertionError('错误批次不能写库')):
            r = self.client.post('/api/import/confirm', json={'projects': [project(), project('')]})
        self.assertEqual(400, r.status_code)
        self.assertIn('error', r.json)

    def test_bad_body_and_unsupported_file_give_readable_errors(self):
        for body in ({}, {'projects': []}, {'projects': '不是列表'}, {'projects': [None]}):
            r = self.client.post('/api/import/confirm', json=body)
            self.assertEqual(400, r.status_code)
            self.assertIn('error', r.json)
        r = self.client.post('/api/import/preview', data={'file': (io.BytesIO(b'abc'), '截图.png')})
        self.assertEqual(400, r.status_code)
        self.assertIn('error', r.json)

    def test_backup_csv_retains_raw_report_fields(self):
        p = project(material='A')
        with patch('app.fetch_projects', return_value=[p]):
            r = self.client.get('/api/export/csv')
        rows = list(csv.DictReader(io.StringIO(r.data.decode('utf-8-sig'))))
        self.assertEqual('A', json.loads(rows[0]['开发报告原始资料'])['fields']['材料型号'])

    def test_report_export_retains_customer_material_and_source(self):
        p = project(material='A')
        with patch('app.fetch_projects', return_value=[p]):
            r = self.client.get('/api/export/report')
        self.assertEqual(200, r.status_code)
        rows = list(csv.DictReader(io.StringIO(r.data.decode('utf-8-sig'))))
        self.assertEqual('示例客户', rows[0]['客户'])
        self.assertEqual('A', rows[0]['材料型号'])
        self.assertEqual('开发', rows[0]['来源工作表'])

    def test_expanded_excel_confirmation_can_exceed_upload_size(self):
        records = []
        for index in range(200):
            record = project(f'大批次-{index}')
            record['reportData'] = json.dumps({'fields': {'备注': 'a' * 28000}}, ensure_ascii=False)
            records.append(record)
        response = service.requests.Response(); response.status_code = 201; response._content = b'[]'
        with patch('app.fetch_projects', return_value=[]), patch('requests.post', return_value=response):
            r = self.client.post('/api/import/confirm', json={'projects': records})
        self.assertEqual(200, r.status_code)
        self.assertEqual(200, r.json['importedCount'])

    def test_file_upload_still_limited_to_five_megabytes(self):
        r = self.client.post('/api/import/preview', data={'file': (io.BytesIO(b'a' * (5 * 1024 * 1024 + 1)), 'large.csv')})
        self.assertIn(r.status_code, (400, 413))
        self.assertIn('5 MB', r.json['error'])
        r.request.environ['wsgi.input'].close()

    def test_report_export_can_be_previewed_again_with_tax_price(self):
        p = project(material='A')
        raw = json.loads(p['reportData']); raw['fields']['单价（含税）元'] = '1.25'
        p['reportData'] = json.dumps(raw, ensure_ascii=False)
        with patch('app.fetch_projects', return_value=[p]):
            exported = self.client.get('/api/export/report')
        preview = self.client.post('/api/import/preview', data={'file': (io.BytesIO(exported.data), 'report.csv')})
        self.assertEqual(200, preview.status_code)
        record = preview.json['sheets'][0]['rows'][0]['project']
        self.assertEqual('1.25', json.loads(record['reportData'])['fields']['单价（含税）元'])

    def test_report_export_does_not_fabricate_sources_for_basic_projects(self):
        with patch('app.fetch_projects', return_value=[project()]):
            exported = self.client.get('/api/export/report')
        self.assertEqual(200, exported.status_code)
        self.assertEqual([], list(csv.DictReader(io.StringIO(exported.data.decode('utf-8-sig')))))

    def test_malformed_metadata_returns_readable_error_instead_of_server_error(self):
        for raw in ('[]', 'null', '{"fields":[]}'):
            p = project(); p['reportData'] = raw
            with patch('app.fetch_projects', return_value=[p]):
                r = self.client.get('/api/export/report')
            self.assertEqual(400, r.status_code)
            self.assertIn('error', r.json)


if __name__ == '__main__':
    unittest.main()
