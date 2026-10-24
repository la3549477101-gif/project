# 界面英文缩写中文注释实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在项目跟踪界面中为常见英文缩写并列显示中文解释。

**Architecture:** 只改 Vue 页面现有文案，不改变 API、数据库或 CSV 数据值。中文括注直接显示在缩写旁，兼顾触屏使用。

**Tech Stack:** Vue 3 单文件组件，HTML 模板。

**Spec:** `docs/superpowers/specs/2026-10-23-ui-abbreviation-explanations-design.md`

## Global Constraints

- 保留 EVT、DVT、PVT、MP、ODM、CSV 原有标识。
- 数据库字段、API 值、CSV 表头和导入导出格式不变。
- 不改布局、字段结构、后端行为或数据迁移。
- 本次不新增或运行测试。

## Review Focus

- 新建、筛选和表格阶段徽标仍使用 EVT、DVT、PVT 原值，注释只改变显示；归属任务：模板修改后检查 option value 与显示映射。
- CSV 的导入导出文案不改变请求接口和文件内容；归属任务：模板修改后检查按钮属性和 API 调用保持原样。
- ODM/MP 注释在表头、表单和统计处均可见；归属任务：模板修改后逐项核对所有界面缩写位置。

---

### Task 1: 在项目跟踪页面补充缩写中文解释

**Files:**
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: 现有项目字段、阶段值和 `api` 调用。
- Produces: 页面中并列显示中文解释的字段、阶段、统计标题和导入导出操作文案。

- [x] **Step 1: 更新页面文案**

在标题、ODM 集成商表头/字段旁说明 ODM（原始设计制造商）；在阶段统计、表格徽标、筛选和编辑选项旁说明 EVT（工程验证测试）、DVT（设计验证测试）、PVT（生产验证测试）；在 MP 日期表头/字段旁说明 MP（量产）；在 CSV 导入导出按钮及相关提示旁说明 CSV（逗号分隔值）。保留各 option 原有 value 和全部 API 绑定。筛选框加宽以展示阶段中文注释。

- [x] **Step 2: 检查源码差异**

检查 `frontend/src/App.vue` 和 `frontend/src/style.css` 的源码，确认缩写注释覆盖上述位置，阶段 option value、数据库值和 API 调用未变。通过静态搜索核对显示位置；未运行测试。

## Implementation Ruling

- **Ruling:** 将阶段筛选框宽度从桌面 140px / 窄屏 120px 调整为 180px / 200px — 原宽度无法完整显示中文阶段注释，因此这项小幅宽度调整让用户能直接读到说明 — 窄屏搜索框可用宽度会缩小，但仍可输入并自动占用剩余空间。
