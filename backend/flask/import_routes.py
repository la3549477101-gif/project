"""Preview before writing; retain the original report alongside basic fields."""
import csv
import io
import json
from threading import Lock

import requests
from flask import Response, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from import_parser import REPORT_HEADERS, canonical_header, read_import, validate_project


def fingerprint(project):
    data = validate_project(project)
    data['customerId'] = project.get('customerId')
    raw = data.pop('reportData', None)
    if raw:
        metadata = json.loads(raw)
        data['reportFields'] = metadata['fields']
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def register_import_routes(app, spring_api, fetch_projects):
    import_lock = Lock()

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return jsonify(error='单个文件最多 5 MB，确认数据最多 64 MB，请拆分后重试'), 413

    @app.before_request
    def bound_file_request():
        if request.path in ('/api/import/preview', '/api/import/csv'):
            # Allow multipart field overhead, while read_import checks file bytes.
            request.max_content_length = 5 * 1024 * 1024 + 64 * 1024

    @app.post('/api/import/preview')
    def preview_import():
        uploaded = request.files.get('file')
        if not uploaded or not uploaded.filename:
            return jsonify(error='请选择 CSV、XLS 或 XLSX 表格文件；文件夹请先打开再选择里面的表格'), 400
        try:
            return jsonify(read_import(uploaded.read(), uploaded.filename))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/api/import/confirm')
    def confirm_import():
        body = request.get_json(silent=True)
        records = body.get('projects') if isinstance(body, dict) else None
        if not isinstance(records, list) or not records or len(records) > 5000:
            return jsonify(error='请选择 1 到 5000 条已检查的记录后再确认导入'), 400
        try:
            prepared = []
            for index, record in enumerate(records, start=1):
                try:
                    prepared.append(validate_project(record))
                except ValueError as exc:
                    raise ValueError(f'第 {index} 条待导入记录：{exc}') from exc
            # Keep concurrent confirmations from creating duplicate copies in this app process.
            with import_lock:
                existing = fetch_projects()
                seen = {fingerprint(project) for project in existing}
                additions, skipped = [], 0
                for project in prepared:
                    key = fingerprint(project)
                    if key in seen:
                        skipped += 1
                    else:
                        seen.add(key)
                        additions.append(project)
                if additions:
                    response = requests.post(f'{spring_api}/projects/import', json=additions, timeout=30)
                    if 400 <= response.status_code < 500:
                        return jsonify(error='数据校验未通过，本批次未导入，请检查字段格式与长度'), 400
                    response.raise_for_status()
            return jsonify(importedCount=len(additions), skippedCount=skipped)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except requests.RequestException:
            return jsonify(error='无法连接项目数据库服务，请检查应用是否启动；网络中断后可重试，相同记录会自动跳过'), 502

    @app.get('/api/export/report')
    def export_report():
        try:
            records = fetch_projects()
        except requests.RequestException:
            return jsonify(error='无法连接项目数据库服务，请检查应用是否启动'), 502
        headers = list(REPORT_HEADERS) + ['实际客户', '原单价表头', '开发报告原始资料', '来源工作表', '来源文件', '来源行号']
        reports = []
        for project in records:
            if not project.get('reportData'):
                continue
            try:
                metadata = json.loads(validate_project(project)['reportData'])
                raw_fields = dict(metadata.get('fields') or {})
            except (ValueError, TypeError):
                return jsonify(error='部分项目的原始资料格式异常，请先检查该项目，未导出不完整的报告'), 400
            # One normalized report column per meaning. The backup JSON retains
            # the exact source labels, including tax wording and extra columns.
            fields = {}
            for key, value in raw_fields.items():
                canonical = canonical_header(key)
                if canonical in REPORT_HEADERS:
                    fields[canonical] = value
                    if canonical == '单价':
                        fields['原单价表头'] = key
            fields['开发报告原始资料'] = project.get('reportData') or ''
            fields['实际客户'] = project.get('customerName') or ''
            if project.get('customerName'):
                fields['客户'] = project['customerName']
            fields['项目名称'] = project.get('projectName') or ''
            fields['终端客户'] = project.get('terminalCustomer') or ''
            fields['应用'] = project.get('application') or ''
            if project.get('expectedMpDate'):
                fields['预估量产时间'] = project['expectedMpDate']
            reports.append((fields, metadata))
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(headers)
        for fields, metadata in reports:
            row = {**fields, '来源工作表': metadata.get('sheet', ''), '来源文件': metadata.get('file', ''), '来源行号': metadata.get('row', '')}
            writer.writerow([row.get(key, '') for key in headers])
        return Response('\ufeff' + stream.getvalue(), content_type='text/csv; charset=utf-8',
                        headers={'Content-Disposition': 'attachment; filename=project-development-report.csv'})
