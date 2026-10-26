import csv
import io
import unittest
from unittest.mock import patch
import app
from import_routes import fingerprint
from import_parser import validate_project, read_import


class CustomerImport(unittest.TestCase):
    def test_customer_ownership_is_part_of_fingerprint(self):
        p = {'projectName': '合成项目', 'customerId': 1}
        self.assertNotEqual(fingerprint(p), fingerprint(dict(p, customerId=2)))
        self.assertEqual(fingerprint({'projectName': '合成项目'}), fingerprint({'projectName': '合成项目', 'customerId': None}))
        self.assertEqual(validate_project(p)['customerId'], 1)
        for invalid in [True, -1, 0, '1', 1.5]:
            with self.assertRaises(ValueError):
                validate_project(dict(p, customerId=invalid))

    def test_export_roundtrip_preserves_customer_candidate_without_trusting_id(self):
        with patch('app.fetch_projects', return_value=[{'projectName': '合成项目', 'customerId': 7, 'customerName': '示例公司'}]):
            response = app.app.test_client().get('/api/export/csv')
        rows = list(csv.DictReader(io.StringIO(response.data.decode('utf-8-sig'))))
        self.assertEqual(rows[0]['实际客户'], '示例公司')
        preview = read_import(response.data, 'backup.csv')
        row = preview['sheets'][0]['rows'][0]
        self.assertEqual(row['customerCandidate'], '示例公司')
        self.assertIsNone(row['project'].get('customerId'))

    def test_folder_service_refuses_user_paths(self):
        client = app.app.test_client()
        self.assertEqual(client.post('/api/customers/1/folder', json={'path': 'C:/fake'}).status_code, 400)
        self.assertEqual(client.post('/api/customers/1/folder', data={}).status_code, 400)
