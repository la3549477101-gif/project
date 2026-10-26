# ODM 项目需求跟踪

## 架构

- `frontend`：Vue 3 + Vite 用户界面。
- `backend/springboot`：Spring Boot 项目主数据 API，使用 H2 文件数据库保存项目记录。
- `backend/flask`：Flask 统计、Excel/CSV 导入预览与导出服务，通过 HTTP 调用 Spring Boot API。

## 环境

- Node.js 20.19+ 或 22.12+（Vite 8 要求）
- Java 17 或更新版本
- Maven 3.9 或更新版本
- Python 3.10 或更新版本

## 本地启动

### 这台电脑已配置的环境

双击本目录的 `start-app.cmd` 可启动三个服务并打开浏览器；使用完双击 `stop-app.cmd` 关闭服务。启动器使用已配置的 Python，不受 PowerShell 脚本执行策略影响，不需要管理员权限。日志保存在 `logs` 目录。此入口依赖当前工作区已安装的工具、项目依赖和已构建的后端 JAR；源码压缩包本身不包含这些大文件。

数据库只读问题已通过正常 Windows 进程运行方式解决；实际页面新增、整套应用停止再启动、重启后编辑保存和 CSV 导出已通过验证。另有隔离数据库上的 25 项检查通过。启动器会检查数据库是否可写，详细结果见 `功能验证记录.md`。

运行工具安装在工作区的 `.tools` 目录，Flask 依赖安装在 `backend/flask/.venv`。这是本项目使用的独立环境；普通终端需要先加载 `environment.ps1` 才能找到这些命令。

开发时可使用下面的 PowerShell 入口（需要本机允许运行本地 PowerShell 脚本）。日常使用请双击 `start-app.cmd`：

```powershell
# 终端 1
./run.ps1 springboot

# 终端 2
./run.ps1 flask

# 终端 3
./run.ps1 frontend
```

然后打开 `http://127.0.0.1:5173`。每个服务可以在对应终端按 Ctrl+C 停止。

只加载命令环境时使用：

```powershell
. ./environment.ps1
node --version
npm.cmd --version
java -version
mvn.cmd --version
python --version
```

`environment.ps1` 使用当前工作区的相对目录和本机 Python 虚拟环境，不适用于把源码单独复制到另一台电脑的情况。前端依赖版本记录在 `frontend/package-lock.json`，Python 依赖版本记录在 `backend/flask/requirements-lock.txt`。

### 其他电脑手动配置

依次在三个终端中启动服务。

### 1. Spring Boot 主数据服务

```powershell
cd backend/springboot
mvn spring-boot:run
```

服务地址：`http://localhost:8080`

### 2. Flask 统计与 CSV 服务

```powershell
cd backend/flask
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

服务地址：`http://localhost:5000`

### 3. Vue 3 前端

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 Vite 打印出的地址，通常为 `http://localhost:5173`。

前端直接通过 Spring Boot 进行项目增删改查，通过 Flask 读取汇总并处理 CSV 导入导出。Spring Boot 的 H2 数据文件保存在 `backend/springboot/data/`。

## 表格导入（2026-10-24 更新）

点击“导入项目数据”，选择 CSV、XLS 或 XLSX。支持原九字段项目清单和十八列项目开发报告。先检查预览，补填缺失的项目名称，再勾选并确认当前工作表。完全相同记录跳过，其他变化新增，不自动覆盖旧记录。文件夹请先打开，再选择里面的表格。

空模板会显示“没有项目记录”，不会写入空项目。Word/PDF/图片识别、AI API 接入仍属于后续开发。

原九字段 CSV 表头：终端客户、ODM集成商、模组厂、项目名称、应用、目前阶段、测试阶段需求数量、项目预计总需求量、预计MP日期。

“导出项目数据”备份所有项目及原始报告资料；“导出开发报告”只导出保留了原报告资料的记录，采用十八业务列加原单价表头、原始资料、来源列的 CSV 格式，可用 Excel 打开。不是原 XLS 的版式复刻。

详细使用步骤、字段映射与限制见 `docs/导入功能使用说明.md`；最新进度和验收记录见 `docs/工作进度_2026-10-24.md`。

## 公司工作台与本周更新（2026-10-26）

左侧“全部客户”按实际采购公司集中查看项目与变更记录。新建客户后自动建立桌面客户文件夹，失败可在客户页面重试。公司与终端客户分别记录；原有项目先放在“未归属项目”，可勾选后统一归属到已建客户。公司改名不改变客户编号，也不移动已有文件夹。

“本周更新”包含客户和项目的新增、修改，显示每次实际变化和所属公司，支持公司筛选、分页和查看原记录。按北京时间周一00:00至下周一00:00统计；旧项目不会被自动算成本周新增，打开后原样保存、导出、重复导入跳过不产生更新。

导入预览可选择本次所选记录的采购公司。原表客户名称仅作候选提示，不自动匹配或建客户；多公司报告可分批勾选导入。项目导出增加可选“实际客户”列，重导入时需人工确认归属，不直接恢复其他数据库的客户编号。项目CSV不是客户主档、所有变更历史或桌面文件的完整备份。

当前客户主档是基本资料版，订单、多型号规格明细、交易条件、Word自动生成、截图识别与AI服务仍按后续计划建设。最新接续开发说明见 `docs/开发进度与后续计划.md`。升级前请停止应用并备份整个 `backend/springboot/data` 目录；不要把业务数据库或客户文件夹上传到公开仓库。
