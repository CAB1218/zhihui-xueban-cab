# 代码运行说明（智慧学伴 / AI4EDU）

> 面向：拿到本仓库、需要在**自己电脑上把项目跑起来**的人（或对方的 AI 助手）。
> 目标：不读源码，只照本文档从上往下执行，30 分钟内看到登录页并能登录。
>
> 仓库地址：`https://github.com/CAB1218/zhihui-xueban-cab`
> 文档版本：2026-11-13 | 对应提交：`4425542` 及以上

---

## 0. 怎么用这份文档

**发给别人时**，把仓库链接和下面这句话一起发过去即可：

> 拉这个仓库跑起来，照着仓库根目录的 `RUNNING.md` 做，跑完用第 5 节的验收清单自查。
> 如果由 AI 代跑，让它先读 `AGENTS.md` 再读 `RUNNING.md`。

**给对方的 AI 一句话启动指令**（可直接复制）：

```
请克隆 https://github.com/CAB1218/zhihui-xueban-cab ，先读仓库根目录的 AGENTS.md
和 RUNNING.md，按“方案 A：Docker 一键启动”执行到第 5 节验收清单全部通过为止。
遇到报错先对照 RUNNING.md 第 8 节排错表，不要擅自删除数据卷（禁止 docker compose down -v），
不要提交 .env / node_modules / dist。
```

---

## 1. 项目速览

| 项 | 内容 |
|---|---|
| 产品名 | 智慧学伴（原 AI4EDU，代码内包名/库名保留 ai4edu） |
| 前端 | Vue 3 + TypeScript + Vite 8 + Element Plus + Pinia + ECharts/D3 |
| 后端 | FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + Celery |
| 数据层 | PostgreSQL（主库）+ Neo4j（知识图谱）+ Redis（缓存/队列）+ ClickHouse（分析）+ Elasticsearch（搜索）+ MinIO（对象存储）+ ChromaDB（向量） |
| 默认入口 | 前端 `http://localhost`，API 文档 `http://localhost:8000/docs` |
| 默认账号 | `admin@ai4edu.com` / `admin123`（super_admin） |

**两条路径，按需选一条：**

- **方案 A（推荐，先跑通）**：Docker Compose 起全部服务，一条命令，不需要在本机装 Python/Node 依赖树。
- **方案 B（要改代码时）**：中间件用 Docker，后端与前端在本机跑（热更新 + 断点调试）。

---

## 2. 环境准备

### 2.1 必备

| 工具 | 版本 | 说明 |
|---|---|---|
| **Docker Desktop** | ≥ 4.30（Compose ≥ **v2.24**） | 必须；compose 文件用了 `env_file: path/required` 语法，老版本会直接报错 |
| **Node.js** | **22.12+**（vite 8 要求 20.19+/22.12+） | 方案 A 构建前端产物、方案 B 起 dev server 都要 |
| **Git** | ≥ 2.30 | 拉代码 |
| **Python** | **3.11**（与后端镜像一致） | 仅方案 B 需要；3.12 可用，3.13 未充分验证（部分依赖需编译） |

### 2.2 机器要求

- 内存：**≥ 8 GB**（同时起 10 个容器，ES + Neo4j 比较吃内存，16 GB 更稳）
- 磁盘：≥ 10 GB 空闲（镜像 + 数据卷）
- 系统：Windows 10/11（开 WSL2）、macOS 12+、Ubuntu 20.04+/Debian 11+

### 2.3 自检（30 秒）

```bash
docker --version            # 期望 Docker version 24+
docker compose version      # 期望 Docker Compose version v2.24+
node -v                     # 期望 v22.12.0 及以上
git --version
# 方案 B 才需要
python --version            # 期望 3.11.x
```

> ⚠️ `docker compose` 是**空格**不是横杠。若只有 `docker-compose`（v1），请升级 Docker Desktop。

---

## 3. 方案 A：Docker 一键启动（推荐）

### 步骤 1：拉代码

```bash
git clone https://github.com/CAB1218/zhihui-xueban-cab.git
cd zhihui-xueban-cab
```

### 步骤 2：构建前端静态产物（**不能跳过**）

仓库**不含** `frontend/dist`（已在 .gitignore 中），而 Nginx 容器是把宿主机的 `frontend/dist` 挂载进去的。不构建 = 打开页面空白/403。

```bash
cd frontend
npm install            # 首次约 2~4 分钟
npx vite build         # 只做打包，约 1~2 分钟
cd ..
```

> 为什么不用 `npm run build`：它会先跑 `vue-tsc` 做全量类型检查，本仓库存在若干历史 TS 报错，会直接中断构建。**打包用 `npx vite build`**。
> 构建成功的标志：`frontend/dist/index.html` 存在，终端出现 `✓ built in ...`。

### 步骤 3：（可选）环境变量

不建 `.env` 也能启动（`app/config.py` 里有默认值），数据库/中间件地址由 compose 注入。
**只有要用 AI 大模型功能时才需要填 Key**：

```bash
# Windows
copy backend\.env.example backend\.env
# macOS / Linux
cp backend/.env.example backend/.env
```

然后编辑 `backend/.env`，填其中一个即可：`DEEPSEEK_API_KEY` / `QWEN_API_KEY` / `HUNYUAN_API_KEY`。
（也可跳过，跑起来后在页面「模型配置」里填，效果一样。）

> ⚠️ `CORS_ORIGINS` 是 List 字段，**必须写成 JSON 数组**，例如
> `CORS_ORIGINS=["http://localhost","http://localhost:5173"]`。写成逗号分隔会导致后端起不来。

### 步骤 4：启动全部容器

```bash
cd deploy
docker compose up -d --build
```

首次会构建后端镜像并安装 Python 依赖（chromadb、Pillow 等），**约 6~10 分钟**，属正常。
中途如果某一步耗时很久，是 pip 在装包，不要 Ctrl+C。

查看状态：

```bash
docker compose ps
```

期望：`postgres` / `neo4j` / `redis` / `minio` / `elasticsearch` / `clickhouse` 全部 **healthy**，`backend` / `frontend` / `celery-*` 为 **Up**。
Neo4j 首次启动最慢，可能需要 1~2 分钟，`health: starting` 时先等。

全部容器与端口：

| 容器 | 宿主机端口 | 用途 |
|---|---|---|
| ai4edu-frontend | 80 | 前端（Nginx） |
| ai4edu-backend | 8000 | API / Swagger |
| ai4edu-postgres | 5432 | 主库 |
| ai4edu-neo4j | 7474 / 7687 | 图谱浏览器 / Bolt |
| ai4edu-redis | 6379 | 缓存 + 队列 |
| ai4edu-clickhouse | 8123 / 9001 | HTTP / Native |
| ai4edu-elasticsearch | 9200 | 搜索 |
| ai4edu-minio | 9002 / 9003 | 对象存储 API / 控制台 |

### 步骤 5：建表 + 初始化数据（**首次必做**）

不建表接口会直接 500。

```bash
# 仍在 deploy 目录
docker compose exec backend alembic upgrade head

docker compose exec backend python scripts/seed_data.py             # 租户/角色/权限/管理员账号
docker compose exec backend python scripts/init_infra.py            # ClickHouse 表 / ES 索引 / MinIO bucket
docker compose exec backend python scripts/seed_knowledge_graph.py  # Neo4j 数学·物理知识图谱
docker compose exec backend python scripts/seed_notes_resources.py  # 笔记与资源示例
```

每条命令的期望输出：出现 `... 成功` / `已创建` / `Inserted` 之类的日志，**没有 Traceback**。
重复执行是安全的（脚本内部做了幂等判断）。

### 步骤 6：打开

| 入口 | 地址 | 账号 |
|---|---|---|
| 前端 | http://localhost | `admin@ai4edu.com` / `admin123` |
| API 文档 | http://localhost:8000/docs | — |
| 健康检查 | http://localhost:8000/health | 期望 `{"status":"healthy"}` |
| Neo4j Browser | http://localhost:7474 | `neo4j` / `neo4j_password` |
| MinIO 控制台 | http://localhost:9003 | `minioadmin` / `minioadmin` |

> **80 端口被占用**（Windows 上常见于 IIS / 迅雷 / 其他 Web 服务）：编辑 `deploy/docker-compose.yml`，把 frontend 的 `"80:80"` 改成 `"8080:80"`，之后访问 http://localhost:8080 。记得同步把 `CORS_ORIGINS` 加上这个地址。

---

## 4. 方案 B：本地开发（改代码时用）

### 步骤 1：只起中间件

```bash
cd deploy
docker compose up -d postgres neo4j redis minio elasticsearch clickhouse
docker compose ps
```

### 步骤 2：起后端（热更新）

```bash
cd ../backend

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env      # Windows 用 copy .env.example .env

# 建表 + 种子数据（连的是 Docker 里的 PG，宿主机 5432）
alembic upgrade head
python scripts/seed_data.py
python scripts/init_infra.py
python scripts/seed_knowledge_graph.py

# 起服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

看到 `Application startup complete.` 即成功。`backend/.env` 默认连 `localhost:5432 / localhost:7687`，与上面的容器端口一致，无需改。

### 步骤 3：起前端（HMR）

另开一个终端：

```bash
cd frontend
npm install
npm run dev
```

看到 `Local: http://localhost:5173/` 即成功。`/api` 与 `/ws` 已由 Vite 代理到 `http://127.0.0.1:8000`（见 `vite.config.ts`），不需要配 CORS。

访问 **http://localhost:5173**。

### 步骤 4：只跑测试（可选）

```bash
cd backend
pytest -q                 # 单测/集成测试
```

---

## 5. 验收清单（跑完逐条自查）

| # | 检查项 | 命令 / 操作 | 通过标准 |
|---|---|---|---|
| 1 | 后端存活 | `curl http://localhost:8000/health` | 返回 `{"status":"healthy",...}` |
| 2 | 建表完成 | `docker compose exec postgres psql -U ai4edu -d ai4edu -c "\dt"` | 列出 `users` / `courses` / `tenants` / `alembic_version` 等表 |
| 3 | 种子数据 | 用 `admin@ai4edu.com` / `admin123` 登录 | 登录成功，进入首页而非 401 |
| 4 | 前端可用 | 浏览器打开 http://localhost（或 :5173） | 出现「智慧学伴智能体」登录页，F12 Console 无红色报错 |
| 5 | 图谱可用 | 左侧进入「知识图谱」 | 能看到数学/物理学科节点（说明 Neo4j 种子成功） |
| 6 | AI 对话 | 进入「AI 智能体」发一句话 | 有回复；未配 Key 时回复会标注「离线回答 · 未调用大模型」，属预期 |

6 条全过 = 环境完全就绪。

---

## 6. 目录导航（要找东西时看这里）

```
ai4edu/
├── RUNNING.md              ← 本文档（怎么跑）
├── AGENTS.md               ← 给 AI 助手的执行规程
├── README.md               ← 项目介绍 + 开发规范 + 更多排错
├── backend/
│   ├── app/
│   │   ├── main.py         ← FastAPI 入口、中间件、路由注册
│   │   ├── config.py       ← 全部配置项与默认值（排查 env 问题先看它）
│   │   ├── api/v1/         ← 每个业务模块一个文件（auth/users/scenes/graphs/...）
│   │   ├── models/         ← ORM 表结构
│   │   ├── schemas/        ← 请求/响应契约
│   │   ├── services/       ← 业务逻辑
│   │   ├── agents/         ← AI 智能体（LangChain）
│   │   └── tasks/          ← Celery 异步任务
│   ├── migrations/         ← Alembic 迁移
│   ├── scripts/            ← 建表后要跑的种子脚本
│   └── tests/
├── frontend/
│   ├── src/views/          ← 页面（按业务分目录）
│   ├── src/router/         ← 路由与守卫
│   ├── src/services/       ← API 封装（axios 实例 + 拦截器）
│   ├── src/stores/         ← Pinia
│   └── vite.config.ts      ← 代理 /api、/ws → 8000
├── deploy/
│   ├── docker-compose.yml  ← 10 个服务的编排（前端/后端/celery/pg/neo4j/ch/redis/es/minio）
│   └── nginx/conf.d/       ← Nginx 反代配置
└── docs/                   ← 各模块设计说明（需要细节时再翻）
```

---

## 7. 常用运维命令

```bash
cd deploy

docker compose ps                     # 状态
docker compose logs -f backend        # 后端实时日志（排错第一入口）
docker compose logs -f frontend
docker compose restart backend        # 只重启后端
docker compose stop                   # 暂停（保留容器与数据）
docker compose start                  # 恢复
docker compose down                   # 删容器，保留数据卷（安全）
docker compose down -v                # ⚠️ 连数据卷一起删，数据全丢
docker compose up -d --build backend  # 改了后端代码后重建
```

前端改了代码但走方案 A（Nginx 挂静态）：必须重新 `npx vite build`，然后浏览器 **Ctrl+Shift+R** 强刷（有 PWA 缓存，普通刷新可能拿到旧页面）。

---

## 8. 排错表（按现象查）

| 现象 | 原因 | 处理 |
|---|---|---|
| `pull access denied for minio/minio` | 官方镜像 2025 年已从 Docker Hub 下架 | compose 已改用 `bitnamilegacy/minio`，确认没手动改回去 |
| compose 报 `additional properties 'path' not allowed` | Compose 版本 < 2.24 | 升级 Docker Desktop |
| 后端启动报 `error parsing value for field "CORS_ORIGINS"` | 该字段是 List，被写成了逗号分隔 | 改成 JSON 数组：`["http://localhost"]` |
| 页面空白 / 403 / 502 | 没构建 `frontend/dist`，或 Nginx 缓存了旧后端 IP | 先 `npx vite build`；再 `docker compose restart frontend` |
| 接口 500，日志报 `relation "users" does not exist` | 没跑迁移 | `docker compose exec backend alembic upgrade head` |
| 登录报 401 / 账号不存在 | 没跑种子脚本 | `docker compose exec backend python scripts/seed_data.py` |
| 知识图谱空白 | Neo4j 没种子数据，或容器还没 healthy | 先等 Neo4j healthy，再跑 `seed_knowledge_graph.py` |
| celery-worker 反复重启，日志 `Redis transport requires redis-py 6.1+` | kombu 与 redis 版本冲突 | requirements 已锁 `kombu==5.4.0`，确认没升级 |
| 端口被占用 `bind: address already in use` | 5432/6379/80 等被本机服务占用 | 改 compose 左侧端口号，或先停掉本机服务 |
| 前端打开还是旧界面/旧标题 | PWA Service Worker 缓存 | `Ctrl+Shift+R` 强刷；必要时 DevTools → Application → Clear storage |
| AI 对话一直显示「离线回答」 | 没配大模型 Key，或 Key 余额不足 | 填 `.env` 的 `DEEPSEEK_API_KEY` 等，或页面「模型配置」里填后点「测试连接」 |
| Neo4j 报 `Property values can only be of primitive types` | Neo4j 5 不允许 map 作属性 | 已在代码里序列化为 JSON 字符串，若自改代码注意保持 |
| Windows 下 `docker` 命令找不到 | Docker Desktop 未启动 / WSL2 未开 | 启动 Docker Desktop，开启 WSL2 后重试 |

**通用排错顺序**：`docker compose ps` 看谁不健康 → `docker compose logs --tail=100 <服务>` 看报错 → 对照上表 → 仍不行再贴日志问人。

---

## 9. 重置与清理

```bash
cd deploy

# 只重置数据库数据（保留镜像）：二选一
docker compose down -v && docker compose up -d      # 最快，全部数据清空
# 或只清 PG：
docker compose exec postgres psql -U ai4edu -d ai4edu -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
# 之后重新跑：alembic upgrade head + 4 个 seed 脚本

# 彻底清理（含镜像，换机器前用）
docker compose down -v --rmi local
```

> 重置后**必须**重跑第 3 节步骤 5 的四条命令，否则登录不了。

---

## 10. 给 AI 助手的硬性约束

1. **不要**执行 `docker compose down -v` 或删除 `postgres_data`/`neo4j_data` 等数据卷（会清空用户数据）。
2. **不要**提交 `.env`、`node_modules/`、`frontend/dist/`（均在 .gitignore 中，别用 `git add -f`）。
3. 前端打包只用 `npx vite build`，不要在交付流程里跑 `npm run build`（`vue-tsc` 历史报错会中断）。
4. 改后端代码后：走方案 A 需 `docker compose up -d --build backend`；走方案 B 靠 `--reload` 自动生效。
5. 报错优先看 `docker compose logs <service>`，不要盲目重建全部容器。
6. 端口冲突时改 compose 的**宿主端口**（冒号左边），不要改容器内端口。
7. 无法联网拉镜像时，先确认代理/镜像源，不要修改 `bitnamilegacy/minio` 等已修正过的镜像名。

细节更全的版本见根目录 `README.md`（含团队协作规范、Git 分支策略、模块地图）。

---

## 11. 变更记录

| 日期 | 内容 |
|---|---|
| 2026-11-13 | 新建本文档；补充 Compose ≥2.24 要求、端口修正（ES 实际 9200、ClickHouse 9001、MinIO 9002/9003）、AI 代理约束 |
