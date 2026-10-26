"""Bounded, read-only import preview for the legacy tracker and project reports.

This module has no database or HTTP access. Report fields retain their source
labels and values; only unambiguous fields populate the existing tracker model.
"""
import csv
import datetime as dt
import io
import json
import math
import re
import zipfile
from collections import Counter
from dataclasses import dataclass

CSV_HEADERS = [
    '终端客户', 'ODM集成商', '模组厂', '项目名称', '应用', '目前阶段',
    '测试阶段需求数量', '项目预计总需求量', '预计MP日期',
]
FIELD_MAP = dict(zip(CSV_HEADERS, [
    'terminalCustomer', 'odmIntegrator', 'moduleFactory', 'projectName',
    'application', 'stage', 'testDemandQuantity', 'estimatedTotalDemand',
    'expectedMpDate',
]))
REPORT_HEADERS = [
    '负责人', '日期', '产品线', '案子状况', '客户', '终端客户', '项目名称',
    '应用', '材料型号', '成品规格', '单价', '预估年用量', '预估年营业额',
    '项目状态', '预估量产时间', '竞争对手', '竞争对手单价', '备注',
]

MAX_UPLOAD = 5 * 1024 * 1024
MAX_EXPANDED = 20 * 1024 * 1024
MAX_ROWS = 5000
MAX_COLUMNS = 100
MAX_SHEETS = 20
HEADER_SCAN = 50
MAX_SAFE_INTEGER = 9007199254740991
MAX_REPORT_LENGTH = 64000
_TEXT_FIELDS = tuple(list(FIELD_MAP.values())[:6])
_LABELS = {value: key for key, value in FIELD_MAP.items()}
_ALIASES = {
    '单价(含税)元': '单价',
    '单价(含税)': '单价',
    'ODM(原始设计制造商)集成商': 'ODM集成商',
    '预计MP(量产)日期': '预计MP日期',
}
_BACKUP_HEADER = '开发报告原始资料'
_REPORT_EXPORT_COLUMNS = {_BACKUP_HEADER, '原单价表头', '来源工作表', '来源文件', '来源行号'}


@dataclass
class _Cell:
    text: str = ''
    error: bool = False
    formula: bool = False


def canonical_header(value):
    """Return a matching label without changing the stored source header."""
    text = re.sub(r'\s+', '', value).replace('（', '(').replace('）', ')').lstrip('\ufeff')
    return _ALIASES.get(text, text)


_header = canonical_header


def _utf16_length(value):
    """Use the same length units as Java String.length and browser strings."""
    return len(value.encode('utf-16-le', errors='surrogatepass')) // 2


def _quantity(value, label):
    if value is None or isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, bool):
        raise ValueError(f'{label}必须为 0 到 {MAX_SAFE_INTEGER} 之间的整数')
    if isinstance(value, int):
        number = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        number = int(value)
    elif isinstance(value, str) and re.fullmatch(r'[0-9]+', value.strip()):
        try:
            number = int(value.strip())
        except ValueError:
            raise ValueError(f'{label}数值过长') from None
    else:
        raise ValueError(f'{label}必须为 0 到 {MAX_SAFE_INTEGER} 之间的整数')
    if not 0 <= number <= MAX_SAFE_INTEGER:
        raise ValueError(f'{label}必须为 0 到 {MAX_SAFE_INTEGER} 之间的整数')
    return number


def _iso_date(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value.strip()):
        raise ValueError('预计MP日期需使用有效的 YYYY-MM-DD 日期')
    try:
        return dt.date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        raise ValueError('预计MP日期需使用有效的 YYYY-MM-DD 日期') from None


def _metadata(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str):
        raise ValueError('开发报告原始资料必须为 JSON 文本')
    if _utf16_length(value) > MAX_REPORT_LENGTH:
        raise ValueError('开发报告原始资料不能超过 64000 字')
    try:
        data = json.loads(value)
    except (ValueError, RecursionError):
        raise ValueError('开发报告原始资料不是有效的 JSON') from None
    if not isinstance(data, dict) or not isinstance(data.get('fields'), dict):
        raise ValueError('开发报告原始资料缺少 fields 字段对象')
    if any(not isinstance(key, str) or not isinstance(item, str) for key, item in data['fields'].items()):
        raise ValueError('开发报告原始资料的字段名称和值必须是文本')
    return value


def _normalize_project(project):
    if not isinstance(project, dict):
        raise ValueError('项目数据必须为对象')
    normalized = {}
    errors = []
    for key in _TEXT_FIELDS:
        value = project.get(key)
        label = _LABELS[key]
        if value is None:
            value = ''
        if not isinstance(value, str):
            errors.append(f'{label}必须为文本')
            value = ''
        value = value.strip()
        if key == 'projectName' and value in ('/', '／'):
            value = ''
        normalized[key] = value
        if _utf16_length(value) > 255:
            errors.append(f'{label}不能超过 255 字')
    if not normalized['projectName']:
        errors.append('项目名称不能为空，请补填后导入')
    if normalized['stage'] not in ('', 'EVT', 'DVT', 'PVT'):
        errors.append('目前阶段只能是 EVT、DVT 或 PVT')
    for key in ('testDemandQuantity', 'estimatedTotalDemand', 'expectedMpDate', 'reportData'):
        value = project.get(key)
        try:
            if key in ('testDemandQuantity', 'estimatedTotalDemand'):
                normalized[key] = _quantity(value, _LABELS[key])
            elif key == 'expectedMpDate':
                normalized[key] = _iso_date(value)
            else:
                normalized[key] = _metadata(value)
        except ValueError as exc:
            normalized[key] = value
            errors.append(str(exc))
    if 'customerId' in project:
        identity = project.get('customerId')
        if identity is not None and (isinstance(identity, bool) or not isinstance(identity, int) or not 0 < identity <= MAX_SAFE_INTEGER):
            errors.append('实际客户编号无效，请重新选择客户')
        else:
            normalized['customerId'] = identity
    return normalized, errors


def validate_project(project):
    """Return only the ten supported fields, or raise a field-labelled error."""
    normalized, errors = _normalize_project(project)
    if errors:
        raise ValueError('；'.join(errors))
    return normalized


def _date_text(value, number_format=''):
    # A stored Excel day does not establish day precision when the cell displays
    # only a month/year. Preserve the visible period rather than inventing a day.
    number_format = (number_format or '').lower()
    number_format = re.sub(r'\\.|\[[^\]]*\]', '', number_format).replace('"', '')
    if isinstance(value, dt.time):
        return value.isoformat()
    if 'y' in number_format and 'd' not in number_format:
        return value.strftime('%Y-%m') if 'm' in number_format else value.strftime('%Y')
    if isinstance(value, dt.datetime):
        return value.date().isoformat() if value.time() == dt.time() else value.isoformat()
    return value.isoformat()


def _cell(value, number_format='', *, error=False, formula=False):
    if value is None:
        text = ''
    elif isinstance(value, (dt.datetime, dt.date, dt.time)):
        text = _date_text(value, number_format)
    elif isinstance(value, bool):
        text = 'TRUE' if value else 'FALSE'
    elif isinstance(value, float):
        text = str(int(value)) if math.isfinite(value) and value.is_integer() else str(value)
    else:
        text = str(value)
    return _Cell(text, error, formula)


def _dimensions(rows, columns):
    if columns > MAX_COLUMNS:
        raise ValueError('文件不能超过 100 列')
    if rows > MAX_ROWS + HEADER_SCAN:
        raise ValueError('文件不能超过 5000 条业务行（含表头前说明的总行数过多）')


def _csv_sheets(content):
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            text = content.decode('gb18030')
        except UnicodeDecodeError:
            raise ValueError('CSV 编码无法识别，请使用 UTF-8 或 GB18030') from None
    if '\x00' in text:
        raise ValueError('CSV 含有无效的二进制内容')
    rows = []
    try:
        for row in csv.reader(io.StringIO(text, newline=''), strict=True):
            _dimensions(len(rows) + 1, len(row))
            rows.append([_cell(value) for value in row])
    except csv.Error:
        raise ValueError('CSV 格式损坏、引号未闭合或字段过长') from None
    return [('CSV', rows)]


def _check_zip(content):
    if content[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        raise ValueError('无法读取 XLSX：可能为加密文件或文件扩展名不正确')
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > 2000 or sum(item.file_size for item in members) > MAX_EXPANDED:
                raise ValueError('XLSX 解压后大小不能超过 20 MB，或压缩文件条目过多')
            for item in members:
                if item.flag_bits & 1:
                    raise ValueError('不支持加密的 Excel 文件，请先解除密码保护')
                if item.filename.lower().endswith('.xml'):
                    xml = archive.read(item)
                    # Reject entity declarations before any workbook XML parser.
                    cleaned = xml.replace(b'\x00', b'').upper()
                    if b'<!DOCTYPE' in cleaned or b'<!ENTITY' in cleaned:
                        raise ValueError('XLSX 含有不支持的 XML 实体声明')
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError):
        raise ValueError('XLSX 文件损坏或无法读取，请重新保存后重试') from None


def _xlsx_sheets(content):
    _check_zip(content)
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ValueError('Excel 读取组件 openpyxl 未安装') from None
    workbook = None
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
        if len(workbook.sheetnames) > MAX_SHEETS:
            raise ValueError('文件不能超过 20 张工作表')
        result = []
        for sheet in workbook.worksheets:
            _dimensions(sheet.max_row or 0, sheet.max_column or 0)
            rows = []
            for row in sheet.iter_rows():
                _dimensions(len(rows) + 1, len(row))
                rows.append([_cell(item.value, item.number_format, error=item.data_type == 'e',
                                   formula=item.data_type == 'f') for item in row])
            result.append((sheet.title, rows))
        return result
    except ValueError:
        raise
    except Exception:
        raise ValueError('XLSX 文件损坏、加密或内容不受支持，请重新保存后重试') from None
    finally:
        if workbook is not None:
            workbook.close()


def _xls_sheets(content):
    try:
        import xlrd
    except ImportError:
        raise ValueError('Excel 读取组件 xlrd 未安装') from None
    workbook = None
    try:
        workbook = xlrd.open_workbook(file_contents=content, formatting_info=True, logfile=io.StringIO())
        if workbook.nsheets > MAX_SHEETS:
            raise ValueError('文件不能超过 20 张工作表')
        result = []
        for sheet in workbook.sheets():
            _dimensions(sheet.nrows, sheet.ncols)
            rows = []
            for row_number in range(sheet.nrows):
                cells = []
                for column in range(sheet.ncols):
                    source = sheet.cell(row_number, column)
                    value = source.value
                    number_format = ''
                    if source.ctype == xlrd.XL_CELL_DATE:
                        value = xlrd.xldate_as_datetime(value, workbook.datemode)
                        fmt = workbook.format_map.get(workbook.xf_list[source.xf_index].format_key)
                        number_format = fmt.format_str if fmt else ''
                    elif source.ctype == xlrd.XL_CELL_BOOLEAN:
                        value = bool(value)
                    elif source.ctype == xlrd.XL_CELL_ERROR:
                        value = xlrd.error_text_from_code.get(value, '#ERROR')
                    cells.append(_cell(value, number_format, error=source.ctype == xlrd.XL_CELL_ERROR))
                rows.append(cells)
            result.append((sheet.name, rows))
        return result
    except xlrd.XLRDError as exc:
        if 'encrypt' in str(exc).lower() or 'password' in str(exc).lower():
            raise ValueError('不支持加密的 Excel 文件，请先解除密码保护') from None
        raise ValueError('XLS 文件损坏或格式不受支持，请重新保存后重试') from None
    except ValueError:
        raise
    except Exception:
        raise ValueError('XLS 文件损坏、加密或内容不受支持，请重新保存后重试') from None
    finally:
        if workbook is not None:
            workbook.release_resources()


def _precise_report_date(value):
    text = value.strip()
    match = re.fullmatch(r'(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})日?', text)
    if not match:
        return None
    try:
        return dt.date(*(int(item) for item in match.groups())).isoformat()
    except ValueError:
        return None


def _preview_sheet(name, source_rows, filename):
    sheet = {'name': name, 'format': 'unsupported', 'headers': [], 'rows': [], 'warnings': []}
    header_index = None
    canonical = []
    for index, row in enumerate(source_rows[:HEADER_SCAN]):
        labels = [_header(cell.text) for cell in row]
        if all(label in labels for label in REPORT_HEADERS):
            sheet['format'] = 'report'
        elif all(label in labels for label in CSV_HEADERS):
            sheet['format'] = 'basic'
        else:
            continue
        header_index, canonical = index, labels
        break
    if header_index is None:
        sheet['warnings'].append('未识别到原9列或18列项目报告表头，此工作表未导入')
        return sheet
    required = REPORT_HEADERS if sheet['format'] == 'report' else CSV_HEADERS
    duplicate = [label for label, count in Counter(canonical).items() if label and count > 1]
    if duplicate:
        raise ValueError(f'工作表“{name}”存在重复表头：' + '、'.join(duplicate))
    indexes = {label: canonical.index(label) for label in required}
    sheet['headers'] = list(required)
    raw_headers = [cell.text for cell in source_rows[header_index]]
    auxiliary = (_REPORT_EXPORT_COLUMNS if sheet['format'] == 'report' else {_BACKUP_HEADER}) | {'实际客户'}
    unknown = [label for label in canonical if label and label not in required and label not in auxiliary]
    if unknown:
        if sheet['format'] == 'report':
            sheet['warnings'].append('存在额外列，请核对源文件；无原始资料备份的记录将保留这些列')
        else:
            sheet['warnings'].append('存在未映射的额外列，这些额外列不会导入；请核对后确认或取消')
    if name == '重点项目':
        sheet['warnings'].append('重点项目可能与分类页重复，请核对后选择；系统不会跨工作表自动合并')
    backup_index = canonical.index(_BACKUP_HEADER) if _BACKUP_HEADER in canonical else None
    for offset, row in enumerate(source_rows[header_index + 1:], start=header_index + 2):
        if not any(cell.text.strip() for cell in row):
            continue
        get = lambda label: row[indexes[label]].text if indexes[label] < len(row) else ''
        warnings = []
        source_errors = []
        if any(cell.error for cell in row):
            source_errors.append('原始资料包含 Excel 错误单元格，请核对后重新上传')
        if any(cell.formula for cell in row):
            warnings.append('原始资料包含公式，保留公式文本且不执行计算，请核对')
        backup = row[backup_index].text if backup_index is not None and backup_index < len(row) else None
        if sheet['format'] == 'basic':
            project = {key: get(label) for label, key in FIELD_MAP.items()}
            project['reportData'] = backup
        else:
            project = {key: '' for key in FIELD_MAP.values()}
            for label in ('终端客户', '项目名称', '应用'):
                project[FIELD_MAP[label]] = get(label)
            period = get('预估量产时间')
            project['expectedMpDate'] = _precise_report_date(period)
            if period.strip() and project['expectedMpDate'] is None:
                warnings.append('预估量产时间保留原文，未转换为精确日期；季度、月份和待定时间需人工核对')
            if backup not in (None, ''):
                # Validation below must report invalid backup JSON as a row
                # error. Never replace it silently, or nest it inside itself.
                project['reportData'] = backup
            else:
                fields = {raw_headers[index]: (row[index].text if index < len(row) else '')
                          for index, label in enumerate(canonical) if label and label != _BACKUP_HEADER}
                project['reportData'] = json.dumps(
                    {'fields': fields, 'sheet': name, 'file': filename, 'row': offset},
                    ensure_ascii=False, separators=(',', ':'),
                )
        name_index = indexes['项目名称']
        if name_index < len(row) and row[name_index].formula:
            project['projectName'] = ''
            warnings.append('项目名称来自公式，请填写已确认的项目名称；报告内保留原公式文本')
        project, errors = _normalize_project(project)
        candidate_index = canonical.index('实际客户') if '实际客户' in canonical else None
        candidate = row[candidate_index].text.strip() if candidate_index is not None and candidate_index < len(row) else (get('客户').strip() if sheet['format'] == 'report' else '')
        sheet['rows'].append({'rowNumber': offset, 'project': project, 'customerCandidate': candidate,
                              'errors': source_errors + errors, 'warnings': warnings})
    return sheet


def read_import(content, filename):
    """Parse a bounded upload into a preview; never mutate the source or records."""
    if not isinstance(content, bytes) or not content:
        raise ValueError('上传文件为空或文件内容无效')
    if len(content) > MAX_UPLOAD:
        raise ValueError('上传文件不能超过 5 MB')
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError('请选择有文件名的 CSV、XLS 或 XLSX 文件')
    filename = re.split(r'[\\/]', filename)[-1]
    if len(filename) > 255:
        raise ValueError('文件名称不能超过 255 字')
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    readers = {'csv': _csv_sheets, 'xls': _xls_sheets, 'xlsx': _xlsx_sheets}
    if extension not in readers:
        raise ValueError('不支持此文件类型，请选择 .csv、.xls 或 .xlsx 文件')
    source_sheets = readers[extension](content)
    sheets = []
    business_rows = 0
    for name, rows in source_sheets:
        sheet = _preview_sheet(name, rows, filename)
        business_rows += len(sheet['rows'])
        if business_rows > MAX_ROWS:
            raise ValueError('文件合计不能超过 5000 条业务行')
        sheets.append(sheet)
    if extension == 'csv' and (not sheets or sheets[0]['format'] == 'unsupported'):
        raise ValueError('未找到原9列或18列项目报告表头，请检查 CSV 模板')
    warnings = []
    if not any(sheet['format'] != 'unsupported' for sheet in sheets):
        warnings.append('文件中没有可识别的项目数据工作表')
    return {'fileName': filename, 'sheets': sheets, 'warnings': warnings}
