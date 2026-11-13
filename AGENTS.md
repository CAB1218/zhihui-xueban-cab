# AGENTS.md — 给 AI 编码助手的仓库说明

本文件供 AI 助手（Claude Code / Cursor / Copilot / WorkBuddy 等）在进入本仓库时快速建立正确上下文。
**人类读者请直接看 [RUNNING.md](./RUNNING.md)**（完整运行说明 + 排错表）。

## 1. 这是什么

智慧学伴（代码内沿用 `ai4edu` 命名）——面向大学本科生的 AI 智慧教学平台。
Vue 3 + TS 前端，FastAPI 后端，PostgreSQL / Neo4j / Redis / ClickHouse / Elasticsearch / MinIO / ChromaDB 多数据层。

## 2. 跑起来的最短路径

工作目录约定：所有 compose 命令在 `deploy/` 下执行；前端命令在 `frontend/` 下执行；后端命令在 `backend/` 下执行。

```bash
# 1) 前端产物（仓库不含 dist，必须构建）
cd frontend && npm install && npx vite build && cd ..

# 2) 起全部容器（首次 6~10 分钟）
cd deploy && docker compose up -d --build

# 3) 建表 + 种子（首次必做，缺一则 500 或登录 401）
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_data.py
docker compose exec backend python scripts/init_infra.py
docker compose exec backend python scripts/seed_knowledge_graph.py
docker compose exec backend python scripts/seed_notes_resources.py
```

本机开发（需热更新时）：`docker compose up -d postgres neo4j redis minio elasticsearch clickhouse`，
然后 `backend/` 里 `uvicorn app.main:app --reload`，`frontend/` 里 `npm run dev`（Vite 已代理 `/api`、`/ws` → 8000）。

## 3. 验收（必须全部通过才算跑通）

1. `curl http://localhost:8000/health` → `{"status":"healthy"}`
2. `http://localhost:8000/docs` 可打开 Swagger
3. `admin@ai4edu.com` / `admin123` 能登录
4. 前端页面 Console 无红色报错
5. 「知识图谱」能显示数学/物理学科节点
6. 详见 RUNNING.md 第 5 节

## 4. 技术约束（易踩坑，务必遵守）

- **前端打包用 `npx vite build`**。`npm run build` 会先跑 `vue-tsc` 全量类型检查，仓库存在历史 TS 报错，会中断构建。
- **Compose 需 ≥ v2.24**，`deploy/docker-compose.yml` 使用了 `env_file: {path, required}` 语法。
- **`CORS_ORIGINS` 是 List**，只能是 JSON 数组；逗号分隔会让后端起不来。
- **仓库不含 `frontend/dist`**（.gitignore），Nginx 容器挂载该目录，不构建就是空白页。
- **MinIO 镜像为 `bitnamilegacy/minio`**（官方镜像 2025 年已下架），不要改回 `minio/minio`。
- **kombu 锁定 5.4.0**，与 `redis==5.0.4` 配套，升级会导致 celery worker 崩溃重启。
- 后端容器以 4 个 uvicorn worker 运行；改代码后需 `docker compose up -d --build backend`。
- 前端有 PWA 缓存，改完重新 build 后需强刷（Ctrl+Shift+R）。

## 5. 禁止操作

- ❌ `docker compose down -v`、删除命名数据卷、`DROP DATABASE`（会清空数据）
- ❌ 提交 `.env`、`node_modules/`、`frontend/dist/`（`git add -f` 也不行）
- ❌ 把真实 API Key / 密钥写入任何入库文件（`.env.example` 只放占位符）
- ❌ 修改容器内端口；端口冲突请改 compose 的宿主端口（冒号左侧）

## 6. 代码地图

| 位置 | 作用 |
|---|---|
| `backend/app/main.py` | FastAPI 入口、中间件、路由注册 |
| `backend/app/config.py` | 全部配置项与默认值（env 问题的第一现场） |
| `backend/app/api/v1/*.py` | 每业务模块一个路由文件，汇总在 `router.py` |
| `backend/app/services/` | 业务逻辑；`*_service.py` |
| `backend/app/models/` / `schemas/` | ORM 表 / Pydantic 契约 |
| `backend/app/agents/` | 12+ 个 AI 智能体（LangChain） |
| `backend/migrations/` | Alembic 迁移，改表后 `alembic revision --autogenerate` |
| `backend/scripts/` | 种子与运维脚本（幂等，可重复执行） |
| `frontend/src/views/` | 页面，按业务分目录 |
| `frontend/src/router/` | 路由、守卫、按角色挂载 |
| `frontend/src/services/` | API 封装（axios 实例已含 `/api/v1` 前缀，勿重复拼） |
| `frontend/vite.config.ts` | 开发代理 `/api`、`/ws` → `127.0.0.1:8000` |
| `docs/` | 各模块 PRD / 架构 / 修复记录 |

## 7. 验证与测试

```bash
cd backend && pytest -q          # 单元 + 集成测试
cd frontend && npm run test      # vitest
```

修改后最低要求：`python -c "import app.main"` 能通过（语法/导入无错）+ 上述验收清单不回归。

## 8. 文档索引

- `RUNNING.md` — 运行说明、端口表、排错表、重置流程（**首选**）
- `README.md` — 项目介绍、目录详解、Git 协作规范、更多历史坑
- `docs/` — 各模块设计说明与修复记录（如 `fix-graph-node-import-edit.md`）
