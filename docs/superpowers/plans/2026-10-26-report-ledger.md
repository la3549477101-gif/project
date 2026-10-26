# 原报告格式主表 Implementation Plan

> For agentic workers: use superpowers:executing-plans inline. Preserve the installed checkout and local data; no new public release.

**Goal:** 按用户指定的18列报告展示和集中编辑项目业务，导出同一份数据到Excel。

**Architecture:** Spring统一生成报告行：旧项目直接读取保留的reportData，无自动合并或转订单；已有型号规格逐条展示，避免新旧数据脱节。统一保存接口在项目行锁内校验版本并更新项目/明细及历史。Vue报告表及编辑弹窗接入所有项目视图。Flask使用现有openpyxl依赖输出四张18列工作表。

**Tech Stack:** Vue3、Spring/JPA/H2、Flask、现有openpyxl。

**Spec / user decisions:** 用户提供原XLS并要求按其格式修改界面；已选择点击编辑后集中核对并保存。保留水下蓝主题、公司/项目/终端三列紧凑固定、公司集中与本周更新。18字段：负责人、日期、产品线、案子状况、客户、终端客户、项目名称、应用、材料型号、成品规格、单价、预估年用量、预估年营业额、项目状态、预估量产时间、竞争对手、竞争对手单价、备注。

## Constraints

- 报告单价与预估年营业额直接可见；不当作订单或收款金额，不自动乘算原始预测；保留币种/数量单位/计价说明。
- 一行一型号规格；无明细的旧项目保留一条原始报告行。原始资料和未知字段保留，不根据相似名称合并或自动建客户。
- 开发/成交/EOL可人工选择，重点为独立标记；本轮不把旧状态文字自动判定为量产或订单。
- 日期/预估量产时间允许原精度文本；案子状况保留原值，不解释未知数字编码。
- 编辑后一次保存，旧版本拒绝覆盖新修改。取消不写入。型号/项目归属校验和既有订单历史不变。
- Excel导出为新XLSX下载，18列按原顺序、四个工作表、保留原始文字，不覆盖用户XLS。文本不执行公式。完整数据库备份另行保留。
- 用户此前已要求检查开发并授权回归，沿用隔离数据库检查；正式升级前离线备份，不用真实资料做公开截图。

## Tasks / Files

- [x] 1. 隔离HTTP失败用例；ReportService/ReportController统一行及原子保存。ProjectDetail及ProjectBusinessService增加报告日期、案子状况、报告分类并保留历史；旧编辑器兼容新增字段。
- [x] 2. ReportLedger.vue、ReportRowEditor.vue主表与集中编辑；App.vue保留项目操作和批量项目选择，接入统一报告行；api.js、ocean-theme.css统一。
- [x] 3. report_export.py和路由输出四表Excel，数据与界面共用Spring报告行；导出防公式并说明作用范围。
- [x] 4. 前后端构建、订单与旧功能隔离回归、合成界面/导出核对、独立审查；离线备份后启动新版，更新文档及本地提交。

## Review Focus

旧元数据完整性、同项目多行与重复选择、编辑冲突/原子性、金额口径/精度、导出四表分类/重点重复及公式保护。原表从不被写入。

## Execution Ledger

- 已只读核对源文件的四工作表和18列表头。原表成交/EOL无业务行；不能据此推导完整成交分类规则。

实现、隔离回归、合成页面/Excel核对及独立只读审查完成，详见docs/acceptance/20261026/report-ledger/验收记录.md。GitHub发布不在本次范围。
