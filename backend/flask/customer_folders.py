"""Only create owned customer folders under the real system desktop."""
import ctypes
import json
import os
import re
import uuid
from pathlib import Path

import requests
from flask import jsonify, request


def desktop_root():
    override = os.getenv('ODM_DESKTOP_ROOT')
    if override:
        return Path(override)
    if os.name != 'nt':
        return Path.home() / 'Desktop'
    guid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID('B4BFCC3A-DB2C-424C-B029-7FE99A87C641').bytes_le)
    result = ctypes.c_wchar_p()
    shell = ctypes.windll.shell32
    shell.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p)]
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    if shell.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(result)) != 0:
        raise ValueError('无法读取系统桌面位置')
    try:
        return Path(result.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(result, ctypes.c_void_p))


def ensure_customer_folder(customer, root=None):
    root = (Path(root) if root is not None else desktop_root()).resolve()
    if not root.is_dir():
        raise ValueError('系统桌面目录不可用')
    identity = customer.get('id')
    if isinstance(identity, bool) or not isinstance(identity, int) or identity <= 0 or not customer.get('createdAt'):
        raise ValueError('客户归档身份无效')
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', customer.get('fullName') or '').strip(' .')[:70] or '客户'
    folder = Path(customer['archivePath']) if customer.get('archivePath') else root / f'{name}--customer-{identity}'
    if not folder.is_absolute() or folder.is_symlink() or folder.resolve().parent != root:
        raise ValueError('客户目录不在固定桌面位置或是链接，请人工核对')
    marker = folder / '.odm-customer.json'
    expected = {'customerId': identity, 'createdAt': customer['createdAt']}
    try:
        folder.mkdir(exist_ok=False)
    except FileExistsError:
        if not folder.is_dir() or marker.is_symlink():
            raise ValueError('客户目录冲突，请人工核对') from None
        try:
            actual = json.loads(marker.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise ValueError('同名目录没有客户归属标记，不会覆盖或合并') from None
        if actual != expected:
            raise ValueError('同名目录属于其他客户或其他数据库，不会覆盖或合并')
    else:
        with marker.open('x', encoding='utf-8') as stream:
            json.dump(expected, stream, ensure_ascii=False)
    return folder.resolve()


def register_customer_folders(app, spring_api):
    @app.post('/api/customers/<int:customer_id>/folder')
    def customer_folder(customer_id):
        # Requiring empty JSON also prevents browser cross-origin form submissions.
        if not request.is_json or request.get_json(silent=True) != {} or customer_id <= 0:
            return jsonify(error='归档请求只能指定已有客户编号'), 400
        try:
            response = requests.get(f'{spring_api}/customers/{customer_id}', timeout=5)
            if response.status_code == 404:
                return jsonify(error='客户不存在'), 404
            response.raise_for_status()
            return jsonify(path=str(ensure_customer_folder(response.json())))
        except requests.RequestException:
            return jsonify(error='客户服务不可用，请稍后重试'), 502
        except (ValueError, OSError) as exc:
            return jsonify(error=f'文件夹创建失败：{exc}'), 409
