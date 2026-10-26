# 公司工作台与本周更新实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将项目归属到实际客户公司，并通过左侧入口查看本周新增和修改。

**Architecture:** Spring Boot 使用固定客户编号和事务内变更日志；Flask负责系统桌面客户文件夹和表格兼容；Vue工作台提供客户列表、项目归属和本周更新。

**Tech Stack:** 现有Vue3、Flask、Spring Boot、H2，不引入新运行时依赖。

**Spec:** `docs/superpowers/specs/2026-10-26-company-workspace-weekly-design.md`（用户已确认）。

## Global Constraints

- 北京时间周一00:00至下周一00:00，只有实际变化才记录；旧数据不回填时间。
- 客户编号与终端/ODM/模组厂分开；未知归属保留为空。
- 保留原九/十八列导入导出与原始资料；应用不覆盖现有桌面目录。
- 现有海洋主题、中文说明、旧数据兼容；在独立数据库和临时桌面验证。

## Review Focus

- 保存无变化与完全重复导入不产生更新：任务1、3。
- 错误客户编号和批量部分失败事务回滚：任务1。
- 目录冲突、非法名称、失败后重试、公司改名：任务2。
- 客户/视图快速切换后旧响应与隐藏勾选：任务4。
- 跨周时区、旧数据、删除后历史和客户转移快照：任务1、5。

### Task 1: 客户、项目归属与事务内变更日志

**Files:** 新增`CustomerRecord/CustomerRepository/ChangeRecord/ChangeRepository/WorkspaceService/CustomerController/ActivityController.java`，修改`ProjectRecord/ProjectController.java`；新增`backend/tests/verify_company_weekly.py`。

**Interfaces:** `/api/customers`增改查；项目`customerId/customerName`；`POST /projects/assign`接收`{ids,customerId}`；`GET /activities?scope=week|all&customerId=&page=&size=`返回`items,total,from,to,timezone`。

- [x] 写独立JAR集成脚本，断言客户重名拒绝、项目归属、无变化不写日志、转移保留原公司、批量错误回滚、周范围、删后历史；先运行看到新接口不存在。
- [x] 增加实体、服务、查询及事务；客户端不能指定审计时间或文件目录。
- [x] 本地Maven离线打包后运行上述脚本。

### Task 2: 客户桌面目录

**Files:** 新增`backend/flask/customer_folders.py`、`tests/test_customer_folders.py`、Spring `CustomerArchiveService.java`，修改`app.py`。

**Interfaces:** Flask `POST /api/customers/<id>/folder`只接受空JSON；读取服务端客户后安全创建固定桌面根目录下目录。Spring创建客户后调用并保存状态，`POST /customers/<id>/folder/retry`重试。

- [x] 编写临时桌面单测，覆盖合法名称、重复请求、未绑定同名目录、符号链接、改名保持路径；先失败再实现。
- [x] 实现系统实际桌面识别、目录归属标记和创建错误提示；不公开写任意路径接口。
- [x] 验证Flask不可用时客户保存成功且可重试。

### Task 3: 表格数据流兼容

**Files:** 修改`app.py/import_parser.py/import_routes.py`，补充`tests/test_import_routes.py`与客户归属回归。

**Interfaces:** `validate_project`保留经校验的`customerId`；导入预览保留实际客户名称候选；导出增加可选“实际客户”列；指纹包含实际客户编号。

- [x] 写归属参与去重和实际客户导出预览往返测试，先失败。
- [x] 实现可选客户字段，不猜客户或自动建客户，不改变旧列文件。
- [x] 运行Flask已有测试和新增测试。

### Task 4: Vue公司工作台

**Files:** 修改`App.vue/api.js/ImportDialog.vue/ocean-theme.css`，新增`CustomerDialog.vue/WeeklyUpdates.vue`。

**Interfaces:** 侧栏切换全部客户、全部项目、本周更新、未归属项目和具体客户；客户弹窗、新建项目与勾选项目指定客户；本周列表按客户筛选并分页，查看变化摘要和对象。

- [x] 先落实API接口与状态隔离，防止陈旧响应覆盖和隐藏项目被选中。
- [x] 实现客户基本资料和目录状态、新建编辑与重试、公司卡片/项目列表、本周历史；导入支持选择本批所属公司及客户候选提示。
- [x] 生产构建通过，使用合成客户和独立数据库做页面验证。

### Task 5: 集成、迁移和交接

**Files:** 更新README、`docs/开发进度与后续计划.md`，新增验收记录。

- [x] 新鲜审阅整个差异；修复重要问题，验证周界限、改名/转移、导入/导出和历史保留。
- [x] 停止正式应用后备份H2再启用新结构，不向正式数据库录入验收数据。
- [x] 更新已完成/待办、构建并重启本机应用，提交已验证代码；不因本轮宣称订单/AI已实现。

## 执行记录

- 已获用户同意直接实施上述设计，本会话内执行，不再就同一方案重复请求确认。
- 在现有已配置运行环境中使用功能分支开发，避免新工作树缺失本机依赖；保留正式数据库并用临时数据库验收。
- Ruling: 可选文本的null、空字符串和首尾空白按同一业务空值比较，避免旧项目打开即保存时产生虚假更新；格式空白调整不单列业务事件。
- 审阅复现：浏览器等价空字段保存曾增加一次虚假修改；新增回归已先运行失败，随后修正比较语义。
- 测试环境修正：覆盖H2 URL时仍显式保留WRITE_DELAY=0，避免测试强制重启丢失尚未落盘的模拟写入。
