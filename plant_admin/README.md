# 中国植物库 · 简易管理端

展示植物数据、简单增删改查、单条导出 JSON（并记入导出日志）。**管理员**可增删改；**普通用户**仅列表查询与导出；**导出记录**登录后均可查看。

## 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0（已执行业务表与扩展表 SQL）

后端使用 **PyMySQL** 直连数据库，**不依赖 SQLAlchemy / greenlet**，在 Windows 上无需安装 Visual C++ 编译工具即可 `pip install`。

## 数据库

1. 在仓库根目录已有 `plant_classification_excel_mysql80.sql`，创建/更新业务表 `plant_classification_import`。
2. 在本目录执行扩展表（仅建表，**不写死任何账号**）：

```bash
mysql -u root -p plant < sql/extend_system_tables.sql
```

（将 `plant` 换成你的库名。）

**登录账号全部来自表 `plant_admin_users`**，后端 `POST /api/auth/login` 只查库、验 bcrypt，应用内没有写死的用户名/密码。

建号（推荐）在配置好 `backend/.env` 后执行：

```bash
cd backend
python create_user.py 管理员账号 '你的强密码' --role admin
python create_user.py 普通用户账号 '你的强密码' --role user
```

已存在用户可加 `--update` 重置密码。仅本地想快速试用时，可**可选**执行 `sql/seed_demo_users.sql`（内含演示 hash，勿用于生产）。

登录页提供**自助注册**（密码 bcrypt 入库）。`.env` 中：`REGISTER_ENABLED`（默认 true）、`REGISTER_ALLOW_ADMIN`（默认 **false**，仅普通用户可自助注册；**内网首次建站**可设为 `true` 以允许网页选择管理员，**公网务必关闭**）。

## 后端

```bash
cd backend
cp .env.example .env
# 编辑 .env：DATABASE_URL、JWT_SECRET（务必改为随机长串）
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 [http://localhost:5173](http://localhost:5173)，使用你在数据库中创建的账号登录。

## API 摘要

- `POST /api/auth/login` — 登录，返回 JWT。
- `GET /api/plants` — 分页列表（需登录）。
- `GET /api/plants/{id}` — 详情。
- `GET /api/plants/{id}/export` — 下载该条 JSON，并写入 `plant_export_logs`。
- `POST|PUT|DELETE /api/plants` — 仅管理员。
- `GET /api/export-logs` — 导出记录（需登录）。

健康检查：`GET /api/health`。
