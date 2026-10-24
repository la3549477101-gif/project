# 项目批量删除实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在项目表格增加多选和安全的批量删除。

**Architecture:** Vue 3 管理当前可见项目的选择状态，并调用 Spring Boot 的批量删除接口。后端在事务中去重、查询并删除所选记录，返回实际删除数量。

**Tech Stack:** Vue 3、Spring Boot、Spring Data JPA。

**Spec:** `docs/superpowers/specs/2026-10-24-project-bulk-delete-design.md`

## Global Constraints

- 延续 `frontend/src/ocean-theme.css` 和海洋主题视觉规范。
- 搜索或阶段筛选变化时清空选择；全选仅作用于当前显示的项目。
- 保留现有单条删除，批量删除执行前必须确认。
- 不引入新依赖，不删除或修改未选项目。

## Review Focus

- 空结果时全选框不可操作，且不显示批量删除栏。
- 部分选中时全选框显示中间态。
- 筛选变化清除选择，避免隐藏项目被删。
- 后端对空、无效、重复及超量 ID 安全处理。
- 删除失败保留记录并在界面显示原因。

---

### Task 1: 后端批量删除接口

**Files:**
- Modify `backend/springboot/src/main/java/com/example/odmtracker/ProjectController.java`

**Interface:** `POST /api/projects/bulk-delete`，请求体为 ID 数组；成功返回 `{"deletedCount": 数量}`。

- [x] 校验 ID 列表并事务内删除实际存在的去重记录，最多 5000 条。

### Task 2: 项目列表多选与确认删除

**Files:**
- Modify `frontend/src/api.js`
- Modify `frontend/src/App.vue`
- Modify `frontend/src/ocean-theme.css`

**Interface:** `api.removeMany(ids)` 调用批量接口；Vue 负责行选择、当前结果全选、确认、成功提示和刷新。

- [x] 添加项目复选框及“已选择 N 个项目”操作栏。
- [x] 筛选变化时清空选择，并通过二次确认执行批量删除。
- [x] 复用海洋主题的青绿焦点样式与珊瑚色危险操作样式。

### Task 3: 构建验证

**Files:** 前后端构建产物。

- [x] 执行前端生产构建和 Spring Boot 编译打包；本次不新增或运行测试。

结果：Vite 8.3.5 生产构建成功；Spring Boot 4.1.2 `package` 成功（`maven.test.skip=true`，未编译或运行测试）；本机应用服务重启并报告 `Ready: http://127.0.0.1:5173/`。
