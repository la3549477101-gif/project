import csv
import io
import os
import re
from datetime import date

import requests
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from import_routes import register_import_routes
from customer_folders import register_customer_folders

app = Flask(__name__)
# Expanded Excel drafts contain both basic fields and original report values.
# File uploads have their own lower limit in register_import_routes.
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173", os.getenv('ODM_FRONTEND_ORIGIN', 'http://127.0.0.1:5173')]}})

SPRING_API = os.getenv("SPRING_API", "http://localhost:8080/api")
CSV_HEADERS = [
    "终端客户", "ODM集成商", "模组厂", "项目名称", "应用", "目前阶段",
    "测试阶段需求数量", "项目预计总需求量", "预计MP日期",
]
FIELD_MAP = {
    "终端客户": "terminalCustomer",
    "ODM集成商": "odmIntegrator",
    "模组厂": "moduleFactory",
    "项目名称": "projectName",
    "应用": "application",
    "目前阶段": "stage",
    "测试阶段需求数量": "testDemandQuantity",
    "项目预计总需求量": "estimatedTotalDemand",
    "预计MP日期": "expectedMpDate",
}


def fetch_projects():
    response = requests.get(f"{SPRING_API}/projects", timeout=10)
    response.raise_for_status()
    return response.json()


@app.get("/api/summary")
def summary():
    try:
        projects = fetch_projects()
    except requests.RequestException as exc:
        return jsonify(error=f"Spring Boot API 不可用：{exc}"), 502
    return jsonify({
        "projectCount": len(projects),
        "testDemandTotal": sum(p.get("testDemandQuantity") or 0 for p in projects),
        "estimatedDemandTotal": sum(p.get("estimatedTotalDemand") or 0 for p in projects),
        "pvtCount": sum(1 for p in projects if p.get("stage") == "PVT"),
    })


@app.get("/api/export/csv")
def export_csv():
    try:
        projects = fetch_projects()
    except requests.RequestException as exc:
        return jsonify(error=f"Spring Boot API 不可用：{exc}"), 502
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    has_report = any(p.get('reportData') for p in projects)
    has_customer = any(p.get('customerName') for p in projects)
    writer.writerow(CSV_HEADERS + (["开发报告原始资料"] if has_report else []) + (["实际客户"] if has_customer else []))
    keys = list(FIELD_MAP.values())
    for project in projects:
        values = ["" if project.get(key) is None else project.get(key) for key in keys]
        if has_report:
            values.append(project.get('reportData') or '')
        if has_customer:
            values.append(project.get('customerName') or '')
        writer.writerow(values)
    content = "\ufeff" + stream.getvalue()
    return Response(
        content,
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=odm-projects.csv"},
    )


def parse_optional_int(value, row_number, field_name):
    value = (value or "").strip()
    if not value:
        return None
    try:
        number = int(value)
        if number < 0 or number > 9007199254740991:
            raise ValueError
        return number
    except ValueError as exc:
        raise ValueError(f"第 {row_number} 行的{field_name}必须为 0 到 9007199254740991 之间的整数") from exc


def parse_optional_date(value, row_number):
    value = (value or "").strip()
    if not value:
        return None
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"第 {row_number} 行的预计MP日期需使用 YYYY-MM-DD 格式") from exc


@app.post("/api/import/csv")
def import_csv():
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify(error="请先选择 CSV 文件"), 400
    try:
        text = uploaded.stream.read().decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        header_index = next((i for i, row in enumerate(rows) if all(h in row for h in CSV_HEADERS)), None)
        if header_index is None:
            return jsonify(error="未找到项目表头，请使用项目跟踪 CSV 模板"), 400
        header = rows[header_index]
        indexes = {name: header.index(name) for name in CSV_HEADERS}
        imported = []
        for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
            if not any(cell.strip() for cell in row):
                continue
            project = {}
            for label, key in FIELD_MAP.items():
                index = indexes[label]
                project[key] = row[index].strip() if index < len(row) else ""
            if not project['projectName']:
                raise ValueError(f"第 {row_number} 行的项目名称不能为空")
            for key in ('terminalCustomer', 'odmIntegrator', 'moduleFactory', 'projectName', 'application'):
                if len(project[key]) > 255:
                    raise ValueError(f"第 {row_number} 行的文字字段不能超过 255 字")
            project["testDemandQuantity"] = parse_optional_int(project["testDemandQuantity"], row_number, "测试阶段需求数量")
            project["estimatedTotalDemand"] = parse_optional_int(project["estimatedTotalDemand"], row_number, "项目预计总需求量")
            project["expectedMpDate"] = parse_optional_date(project["expectedMpDate"], row_number)
            if project["stage"] not in ("", "EVT", "DVT", "PVT"):
                raise ValueError(f"第 {row_number} 行的目前阶段只能是 EVT、DVT 或 PVT")
            imported.append(project)
        if not imported:
            return jsonify(error="CSV 中没有可导入的项目记录"), 400
        response = requests.post(f"{SPRING_API}/projects/import", json=imported, timeout=30)
        if 400 <= response.status_code < 500:
            return jsonify(error='导入数据不符合要求，请检查字段格式和长度'), 400
        response.raise_for_status()
        return jsonify(importedCount=len(imported))
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        return jsonify(error=str(exc)), 400
    except requests.RequestException as exc:
        return jsonify(error=f"Spring Boot API 不可用：{exc}"), 502


register_import_routes(app, SPRING_API, lambda: fetch_projects())
register_customer_folders(app, SPRING_API)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
