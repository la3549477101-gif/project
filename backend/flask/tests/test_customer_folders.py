import json
import tempfile
import unittest
from pathlib import Path

from customer_folders import ensure_customer_folder


class CustomerFolders(unittest.TestCase):
    def test_create_retry_rename_and_ownership(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            c = {'id': 7, 'fullName': '示例/客户:*?', 'createdAt': '2026-10-26T00:00:00Z'}
            path = ensure_customer_folder(c, root)
            self.assertEqual(path.parent, root.resolve())
            self.assertTrue((path / '.odm-customer.json').exists())
            (path / '保留.txt').write_text('原文件', encoding='utf-8')
            self.assertEqual(ensure_customer_folder(c, root), path)
            c.update(fullName='更名公司', archivePath=str(path))
            self.assertEqual(ensure_customer_folder(c, root), path)
            self.assertEqual((path / '保留.txt').read_text(encoding='utf-8'), '原文件')
            c['createdAt'] = '2026-10-27T00:00:00Z'
            with self.assertRaises(ValueError):
                ensure_customer_folder(c, root)

    def test_unowned_directory_and_outside_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            c = {'id': 8, 'fullName': '示例客户', 'createdAt': '2026-10-26T00:00:00Z'}
            (root / '示例客户--customer-8').mkdir()
            with self.assertRaises(ValueError):
                ensure_customer_folder(c, root)
            c['archivePath'] = str(root.parent)
            with self.assertRaises(ValueError):
                ensure_customer_folder(c, root)

    def test_folder_marker_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            c = {'id': 9, 'fullName': '示例客户', 'createdAt': '2026-10-26T00:00:00Z'}
            folder = ensure_customer_folder(c, root)
            marker = folder / '.odm-customer.json'
            marker.write_text(json.dumps({'customerId': 99}), encoding='utf-8')
            with self.assertRaises(ValueError):
                ensure_customer_folder(c, root)


if __name__ == '__main__':
    unittest.main()
