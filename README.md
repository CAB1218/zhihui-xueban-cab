# AI4EDU — AI 驱动的智慧教学平台

[![Repository](https://img.shields.io/badge/GitHub-CAG1218%2Fai4edu-181717?logo=github)](https://github.com/CAG1218/ai4edu)
[![License](https://img.shields.io/badge/license-Proprietary-blue)](#)
[![Stack](https://img.shields.io/badge/frontend-Vue3%20%2B%20TS%20%2B%20Vite-42b883)](https://vuejs.org)
[![Stack](https://img.shields.io/badge/backend-FastAPI%20%2B%20Python%203.11-009688)](https://fastapi.tiangolo.com)

> 大学本科生场景的 AI 智慧教学平台。Vue 3 + Element Plus 前端，FastAPI + 多数据库后端，Docker 一键部署。

---

## 📋 目录

- [项目简介](#-项目简介)
- [环境要求](#-环境要求)
- [端口占用一览](#-端口占用一览)
- [本地启动（两种方式）](#-本地启动两种方式)
  - [方式 A：Docker Compose 一键起（推荐）](#方式-a-docker-compose-一键起推荐)
  - [方式 B：前后端分进程本地开发（推荐用于联调）](#方式-b-前后端分进程本地开发推荐用于联调)
- [目录结构与模块定位](#-目录结构与模块定位)
- [常用调试命令](#-常用调试命令)
- [默认账号](#-默认账号)
- [团队协作规范（Git 分支策略）](#-团队协作规范git-分支策略)
- [常见问题 FAQ](#-常见问题-faq)

---

## 🎯 项目简介

AI4EDU 是面向**大学本科生**的 AI 智慧教学平台，核心场景包括：

- **课堂模式（classroom）**：实时互动、举手、抢答、随堂练习
- **自习模式（self_study）**：知识图谱引导、笔记关联、闪卡复习
- **考前模式（exam）**：模拟考、错题本、考前倒计时
- **讨论模式（discussion）**：小组协作、白板、共享笔记

平台特色：**课程梳理**（输入想学的课程 → 联网检索 + LLM 依据课程标准梳理出学习内容与要求清单、必要联系、材料出处，支持 JSON/Markdown/Word 导出，见 `docs/task1-课程梳理模块说明.md`）、教师工作台、班级诊断、AI 智能体（学科辅导 / 教案生成 / 学习诊断 / 学伴聊天）、知识图谱、文件 RAG。

**技术栈总览**：

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia + ECharts + D3 |
| 后端 | FastAPI + SQLAlchemy 2.0(async) + Pydantic v2 + Celery |
| 数据库 | PostgreSQL 16（主库）+ Neo4j 5（图谱）+ Redis 7（缓存/队列）+ ClickHouse（分析）+ Elasticsearch 8（搜索）+ MinIO（对象存储）+ ChromaDB（向量） |
| 部署 | Docker Compose / Vite Dev Server + Uvicorn |

---

## 🛠 环境要求

### 必备

| 工具 | 版本 | 用途 | 备注 |
|---|---|---|---|
| **Docker Desktop** | ≥ 4.20 | 容器化部署 | 含 docker compose v2；Windows 用户需开启 WSL2 |
| **Node.js** | **22.x** (推荐 22.12.0) | 前端 dev server | 不要用 18.x，部分包不支持 |
| **Python** | **3.11** | 后端开发 | 3.12/3.13 也可，但 Docker 镜像是 3.11 |
| **Git** | ≥ 2.30 | 版本控制 | — |

### 可选

| 工具 | 用途 |
|---|---|
| **pnpm** 或 **npm** | 推荐 npm，仓库已带 package-lock.json |
| **VSCode** | 集成开发；推荐装 `Vue Language Features (Volar)` + `Python` 扩展 |
| **DBeaver / Navicat** | 图形化管理 PostgreSQL/Neo4j |
| **Redis Desktop Manager** | Redis 调试 |
| **cloudflared** | 内网穿透（队友不在同一内网时使用） |

### 操作系统

- **Windows 10/11**（需开启 WSL2 + Hyper-V）
- **macOS 12+**
- **Ubuntu 20.04+ / Debian 11+**

---

## 🔌 端口占用一览

> ⚠️ **启动前请检查这些端口是否被占用**（`netstat -an | grep 端口号`）。若被占用需先释放或修改 `deploy/docker-compose.yml`。

| 端口 | 服务 | 备注 |
|---|---|---|
| **80** | 前端（Nginx 容器） | Docker 部署时访问 http://localhost，即 compose 里的 `80:80` |
| **5173** | Vite Dev Server | 本地前端开发（**前端联调时使用**） |
| **8000** | FastAPI 后端 | API 根入口 |
| **5432** | PostgreSQL | 数据库 |
| **6379** | Redis | 缓存 + Celery broker |
| **7474** | Neo4j Browser | 图谱可视化（http://localhost:7474） |
| **7687** | Neo4j Bolt | 图谱驱动协议 |
| **8123** | ClickHouse HTTP | 分析查询 |
| **9001** | ClickHouse Native | 分析查询（容器内 9000 → 宿主 9001） |
| **9000** | Elasticsearch HTTP | 搜索 |
| **9002** | MinIO API | 对象存储（容器内 9000 → 宿主 9002） |
| **9003** | MinIO Console | 管理控制台（http://localhost:9003，账号 minioadmin / minioadmin） |

---

## 🚀 本地启动（两种方式）

### 方式 A：Docker Compose 一键起（推荐）

**适用场景**：快速验证整个平台是否跑通，不需要频繁改代码。
**实测环境**：Windows 11 + Docker Desktop（引擎 29.9）+ Compose v5.6，Linux 容器模式。

```bash
# 1. 克隆仓库
git clone https://github.com/CAB1218/zhihui-xueban-cab.git
cd zhihui-xueban-cab

# 2. 构建前端静态产物（nginx 挂载的是 frontend/dist，仓库不含产物，必须先构建）
cd frontend
npm install
npx vite build        # 注意：不要用 npm run build，它会先跑 vue-tsc 类型检查，
                      # 仓库里存在若干历史 TS 报错会直接中断构建
cd ..

# 3. （可选）后端环境变量：不建也能启动（config.py 有默认值），
#    只有要用 AI 大模型功能时才需要填 Key
cp backend/.env.example backend/.env
#   然后编辑 backend/.env，填入 DEEPSEEK_API_KEY / QWEN_API_KEY / HUNYUAN_API_KEY 之一

# 4. 启动全部 10 个容器（首次要构建后端镜像并装依赖，约 6~8 分钟）
cd deploy
docker compose up -d --build
docker compose ps     # 等到 postgres / neo4j / redis / minio / elasticsearch / clickhouse 都是 healthy

# 5. 建表（必须执行，否则接口会 500）
docker compose exec backend alembic upgrade head

# 6. 初始化数据（仅首次）
docker compose exec backend python scripts/seed_data.py             # 角色/权限/租户/默认账号
docker compose exec backend python scripts/init_infra.py            # ClickHouse 表 / ES 索引 / MinIO bucket
docker compose exec backend python scripts/seed_knowledge_graph.py  # Neo4j 数学·物理知识图谱
docker compose exec backend python scripts/seed_notes_resources.py  # 笔记与资源示例

# 7. 访问
# 前端：          http://localhost
# 后端 API 文档：  http://localhost:8000/docs
# Neo4j Browser： http://localhost:7474
# MinIO 控制台：   http://localhost:9003
# 默认账号：      admin@ai4edu.com / admin123
```

**已踩过的坑（本仓库已修好，自行部署时对照排查）**

| 现象 | 原因 | 处理 |
|---|---|---|
| `pull access denied for minio/minio` | 官方镜像 2025 年已从 Docker Hub 下架 | compose 已改用 `bitnamilegacy/minio` |
| 后端启动报 `error parsing value for field "CORS_ORIGINS"` | `CORS_ORIGINS` 是 List 字段，必须写成 JSON 数组 | 见 `.env.example` 里的写法 |
| `docker exec ... scripts/seed_data.py` 报文件不存在 | `.dockerignore` 曾排除 `scripts/` | 已改为打进镜像 |
| 前端页面空白 / 404 | nginx 挂载 `frontend/dist`，仓库里没有构建产物 | 先执行上面第 2 步 |
| 知识图谱节点写入报 `Property values can only be of primitive types` | Neo4j 5 不允许 map 作为属性值 | `create_node` 已自动把 dict/list 序列化为 JSON 字符串 |
| celery-worker 反复重启，报 `Redis transport requires redis-py versions 6.1.0 or later` | kombu 5.6+ 与固定的 redis==5.0.4 不兼容 | requirements 已锁定 `kombu==5.4.0` |
| 单独重启 backend 后前端所有接口 502 | nginx 启动时缓存了后端容器旧 IP | nginx 已改为 `resolver 127.0.0.11 valid=10s` + 变量 proxy_pass，自动跟随容器 IP |
| 点击「课堂模式」报 `navigateTo is not a function` | 侧边栏模板绑定了未定义的 `navigateTo` | 已移除（el-menu 的 router 模式本身就会跳转） |
| 页面弹「请求的资源不存在」 | 前端重复拼了 `/api/v1` 前缀 | 已修正，axios 实例 baseURL 已含前缀 |


**停止 / 重启**：
```bash
docker compose stop          # 停止
docker compose start         # 启动
docker compose down          # 停止并删除容器（保留数据卷）
docker compose down -v       # ⚠️ 删容器 + 删数据卷（慎用）
docker compose restart backend  # 单独重启后端
docker compose logs -f backend  # 查看后端实时日志
```

---

### 方式 B：前后端分进程本地开发（推荐用于联调）

**适用场景**：日常开发，需要 HMR 热更新和断点调试。

#### 步骤 1：启动中间件（只起后端需要的依赖）

```bash
cd deploy

# 仅启动数据库/中间件，不起 backend / frontend 容器
docker compose up -d postgres neo4j redis minio elasticsearch clickhouse

# 验证
docker compose ps
```

#### 步骤 2：本地启动后端（带热更新）

```bash
# 创建虚拟环境（首次）
cd ../backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# （可选）准备环境变量
# 默认值已在 app/config.py 中定义，无需 .env 即可启动
# 若要覆盖，新建 backend/.env 文件即可（Pydantic Settings 自动读取）

# 启动开发服务器（带 reload）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 看到 "Application startup complete" 即成功
# API 文档：http://localhost:8000/docs
```

#### 步骤 3：本地启动前端（带 HMR）

```bash
# 另开一个终端
cd frontend
npm install
npm run dev

# 看到 "Local: http://localhost:5173/" 即成功
# 前端会自动把所有 /api/* 请求代理到 http://127.0.0.1:8000
```

#### 步骤 4：初始化数据库（仅首次）

```bash
# 在 backend 目录下
python scripts/seed_data.py              # 租户/用户/角色/权限
python scripts/seed_notes_resources.py   # 笔记/资源
```

#### 访问

- **前端（联调）**：http://localhost:5173
- **后端 API**：http://localhost:8000/docs

---

## 📂 目录结构与模块定位

```
ai4edu/
├── README.md                          ← 本文件
├── start-tunnel.bat                   ← Windows 启动 cloudflared 内网穿透
├── .gitignore
│
├── backend/                           ← 后端（FastAPI）
│   ├── app/
│   │   ├── main.py                    ← FastAPI 入口（CORS / 中间件 / 路由注册）
│   │   ├── config.py                  ← 配置（DB / JWT / OpenAI 等）
│   │   ├── database.py                ← SQLAlchemy 异步引擎
│   │   ├── dependencies.py            ← 鉴权依赖（get_current_user / get_db）
│   │   ├── core/                      ← 核心（安全/异常/Redis/加密/遥测）
│   │   ├── middleware/                ← 中间件（日志/租户/限流/RBAC）
│   │   ├── models/                    ← ORM 模型（20+ 张表）
│   │   │   ├── user.py                ← 用户
│   │   │   ├── course.py              ← 课程
│   │   │   ├── note.py                ← 笔记
│   │   │   ├── resource.py            ← 资源（文件）
│   │   │   ├── knowledge_graph        ← 见 graphs 模型分散在多文件
│   │   │   ├── classroom.py           ← 课堂
│   │   │   ├── lesson_plan.py         ← 教案
│   │   │   ├── diagnosis.py           ← 学习诊断
│   │   │   └── ...
│   │   ├── schemas/                   ← Pydantic 数据契约
│   │   ├── repositories/              ← 仓储层（数据访问封装）
│   │   ├── services/                  ← 业务逻辑层
│   │   │   ├── rag/                   ← RAG 服务（embedder 等）
│   │   │   ├── note_service.py        ← 笔记服务
│   │   │   ├── classroom_service.py   ← 课堂服务
│   │   │   ├── graph_service.py       ← Neo4j 图谱服务
│   │   │   └── ...
│   │   ├── agents/                    ← AI 智能体（LangChain）
│   │   │   ├── intent_router.py       ← 意图路由
│   │   │   ├── rag_agent.py           ← RAG 问答
│   │   │   ├── subject_agent.py       ← 学科辅导
│   │   │   ├── quiz_agent.py          ← 出题
│   │   │   ├── lesson_plan_agent.py   ← 教案生成
│   │   │   ├── diagnosis_agent.py     ← 学习诊断
│   │   │   ├── classroom_agent.py     ← 课堂助手
│   │   │   ├── buddy_agent.py         ← 学伴聊天
│   │   │   ├── psychology_agent.py    ← 心理辅导
│   │   │   ├── file_rag_agent.py      ← 文件 RAG
│   │   │   ├── anti_misconception_agent.py  ← 防误解
│   │   │   └── general_agent.py       ← 通用
│   │   ├── tasks/                     ← Celery 异步任务
│   │   ├── websocket/                 ← WebSocket 服务（课堂 / 通知）
│   │   ├── utils/                     ← 工具函数
│   │   └── api/v1/                    ← HTTP API（v1 版本）
│   │       ├── router.py              ← 路由汇总（17 个子路由）
│   │       ├── auth.py                ← 认证（注册/登录/刷新token）
│   │       ├── users.py               ← 用户管理
│   │       ├── scenes.py              ← 场景（课堂/自习/考前/讨论）
│   │       ├── resources.py           ← 资源 CRUD + 上传下载
│   │       ├── graphs.py              ← 知识图谱
│   │       ├── notes.py               ← 笔记
│   │       ├── search.py              ← 全局搜索
│   │       ├── agents.py              ← AI 智能体调用
│   │       ├── teachers.py            ← 教师工作台
│   │       ├── classrooms.py          ← 课堂互动
│   │       ├── notifications.py       ← 通知
│   │       ├── permissions.py         ← 权限管理
│   │       ├── diagnosis.py           ← 学习诊断
│   │       ├── buddies.py             ← 学伴
│   │       ├── help.py                ← 帮助中心
│   │       ├── governance.py          ← 数据治理
│   │       ├── telemetry.py           ← 遥测
│   │       └── dashboard.py           ← 仪表盘统计
│   ├── scripts/                       ← 数据脚本
│   │   ├── seed_data.py               ← 基础数据（租户/角色/权限）
│   │   └── seed_notes_resources.py    ← 笔记/资源示例数据
│   ├── tests/                         ← pytest 测试
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                          ← 前端（Vue 3 + Vite）
│   ├── src/
│   │   ├── main.ts                    ← 入口（注册 Pinia/Router/i18n）
│   │   ├── App.vue                    ← 根组件（含 ErrorBoundary）
│   │   ├── api/                       ← API 客户端（按业务域拆分）
│   │   ├── components/                ← 通用组件
│   │   │   ├── layout/                ← AppLayout / SceneLayout / Header / Sidebar / BottomNav
│   │   │   ├── common/                ← LoadingSpinner / EmptyState / ConfirmDialog
│   │   │   ├── graph/                 ← ForceGraph / NodeCard / LinkInfo（图谱可视化）
│   │   │   ├── resource/              ← ResourceCard / UploadZone / FilePreview
│   │   │   └── search/                ← SearchBox
│   │   ├── views/                     ← 页面（路由直接对应的组件）
│   │   │   ├── auth/                  ← LoginView / RegisterView
│   │   │   ├── onboarding/            ← StepRoleView / StepInterestsView / StepGoalView
│   │   │   ├── scene/                 ← DashboardView（场景仪表盘）
│   │   │   ├── graph/                 ← GraphSquareView / GraphDetailView
│   │   │   ├── search/                ← SearchView
│   │   │   ├── resource/              ← MyResourcesView / ResourceUploadView / ResourceDetailView
│   │   │   ├── note/                  ← NoteListView / NoteEditView
│   │   │   ├── agent/                 ← AgentChatView（AI 对话）
│   │   │   ├── buddy/                 ← BuddyChatView（学伴聊天）
│   │   │   ├── diagnosis/             ← DiagnosisView
│   │   │   ├── teacher/               ← TeacherDashboard / LessonPlanView / ClassDiagnosisView
│   │   │   ├── admin/                 ← AuditLogView / DataGovernanceView
│   │   │   └── help/                  ← HelpCenterView
│   │   ├── router/                    ← 路由配置
│   │   │   ├── index.ts               ← 入口（合并 constantRoutes + asyncRoutes）
│   │   │   ├── guards.ts              ← 路由守卫（认证 + onboarding 检查）
│   │   │   └── routes/                ← 路由拆分
│   │   │       ├── scene-routes.ts    ← /scene/*（核心场景路由）
│   │   │       ├── teacher-routes.ts  ← /teacher/*
│   │   │       └── admin-routes.ts    ← /admin/*
│   │   ├── stores/                    ← Pinia 状态
│   │   │   └── index.ts               ← 各业务 store
│   │   ├── services/                  ← 服务层（封装 API 调用）
│   │   │   └── api.ts                 ← Axios 实例 + 拦截器
│   │   ├── i18n/                      ← 国际化
│   │   └── styles/                    ← 全局样式（SCSS）
│   ├── package.json
│   ├── vite.config.ts                 ← Vite 配置（代理 /api → 8000）
│   └── tailwind.config.ts
│
├── deploy/                            ← 部署配置
│   ├── docker-compose.yml             ← 8 个服务的编排
│   └── Dockerfile.frontend            ← 前端 Docker 镜像（Nginx）
│
└── midterm/                           ← 中期答辩材料
    ├── 00_提交材料清单.md
    ├── 01_项目说明书.docx
    ├── 03_Demo演示说明.txt
    ├── 04_代码仓库链接.txt
    └── 05_代码运行说明.md
```

### 快速找代码地图（队友必备）

| 我要改… | 看这里 |
|---|---|
| **某个业务接口（后端）** | `backend/app/api/v1/<模块名>.py` —— 17 个模块各一个文件 |
| **接口对应的数据校验/响应格式** | `backend/app/schemas/<模块名>.py` |
| **某个业务逻辑（后端）** | `backend/app/services/<模块名>_service.py` |
| **数据库表结构** | `backend/app/models/<模块名>.py` |
| **AI 智能体的 Prompt / 链** | `backend/app/agents/<名称>_agent.py` |
| **某个页面的 UI（前端）** | `frontend/src/views/<模块>/<Page>View.vue` |
| **路由配置** | `frontend/src/router/routes/<角色>-routes.ts` |
| **API 调用 / HTTP 拦截器** | `frontend/src/services/api.ts` |
| **状态管理** | `frontend/src/stores/index.ts` |
| **路由守卫 / 鉴权** | `frontend/src/router/guards.ts` |
| **前端代理配置（开发时把 /api 转给 8000）** | `frontend/vite.config.ts` |
| **后端配置（DB / JWT / CORS）** | `backend/app/config.py` |
| **种子数据 / 初始化脚本** | `backend/scripts/seed_*.py` |
| **新增服务到 Compose** | `deploy/docker-compose.yml` |

---

## 🔍 常用调试命令

### 后端

```bash
# 进入后端容器
docker exec -it ai4edu-backend bash

# 查看实时日志
docker logs -f ai4edu-backend

# 进入 Python REPL（容器内）
docker exec -it ai4edu-backend python

# 重置数据库（⚠️ 删数据）
docker exec -it ai4edu-postgres psql -U ai4edu -d ai4edu -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker exec -it ai4edu-backend python scripts/seed_data.py
docker exec -it ai4edu-backend python scripts/seed_notes_resources.py
```

### 前端

```bash
# 类型检查
cd frontend && npx vue-tsc --noEmit

# 构建生产包
npm run build

# 预览生产包
npm run preview

# 跑测试
npm run test
```

### 数据库

```bash
# PostgreSQL
docker exec -it ai4edu-postgres psql -U ai4edu -d ai4edu

# Neo4j（浏览器）
# 访问 http://localhost:7474，账号 neo4j / neo4j_password

# Redis
docker exec -it ai4edu-redis redis-cli

# ClickHouse
docker exec -it ai4edu-clickhouse clickhouse-client --password clickhouse_password
```

### 内网穿透（队友不在同一局域网时）

```bash
# Windows 一键起 cloudflared 隧道
cd ai4edu
start-tunnel.bat

# 启动后会输出形如 https://xxxx.trycloudflare.com 的公网地址
# 前端和后端 API 都可访问（前端地址对外提供，后端通过 Vite proxy 转发）
```

---

## 🔐 默认账号

| 角色 | 邮箱 | 密码 |
|---|---|---|
| 超级管理员 | `admin@ai4edu.com` | `admin123` |

> ⚠️ 仅用于本地开发！生产环境务必修改密码并重新生成 `JWT_SECRET_KEY`。

---

## 🤝 团队协作规范（Git 分支策略）

> 🎯 **核心原则**：主分支 (`main`) 保持稳定可用，新功能在特性分支开发，完成后通过 PR 合并。

### 分支命名规范

```bash
git checkout main
git pull origin main
git checkout -b feature/<你的名字>-<功能名>

# 示例
git checkout -b feature/zhang-knowledge-graph-export
git checkout -b fix/wang-frontend-white-screen
git checkout -b refactor/li-api-error-handling
```

### 推荐的工作流

```bash
# 1. 每天开工前同步主分支
git checkout main
git pull origin main

# 2. 拉特性分支开始干活
git checkout -b feature/<name>-<feature>

# 3. 开发中：边改边提交
git add -A
git commit -m "feat: add knowledge graph export button"
git push origin feature/<name>-<feature>

# 4. 完成后推送到远程，在 GitHub 上发 Pull Request
# 5. PR 通过后由主理人（或你）合并到 main
# 6. 合并后删除特性分支
git branch -d feature/<name>-<feature>
git push origin --delete feature/<name>-<feature>
```

### Commit 消息规范

建议遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

| 类型 | 用途 | 示例 |
|---|---|---|
| `feat` | 新功能 | `feat: add knowledge graph export feature` |
| `fix` | 修 bug | `fix: resolve white screen on dashboard` |
| `refactor` | 重构 | `refactor: extract graph rendering to composable` |
| `docs` | 文档 | `docs: update README with deployment steps` |
| `style` | 格式 | `style: format with prettier` |
| `test` | 测试 | `test: add unit tests for note service` |
| `chore` | 杂项 | `chore: bump dependency versions` |

### 推送代码到 GitHub（网络不畅时）

```bash
# 如果直连 GitHub 失败，配置代理（示例，端口以你本地为准）
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890

# 推送
git push origin feature/<name>-<feature>
```

### 避免冲突的小技巧

1. **修改前先 `git pull`**，确保基于最新 `main`
2. **小颗粒度提交**：一个 commit 只做一件事
3. **避免多人同时改同一文件**：分配任务时尽量解耦
4. **复杂 UI 改动先在群里同步**：避免做出来发现和别人重复

---

## ❓ 常见问题 FAQ

### Q1: Docker 起不来 / 端口被占用？
```bash
# 查看占用
netstat -an | grep 8000
# 杀掉
# Windows
netstat -ano | findstr :8000
taskkill /F /PID <pid>
# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

### Q2: 前端白屏 / 控制台报错？
1. 打开浏览器 DevTools → Console
2. 看错误是 Vite HMR、Axios 还是 Vue 组件
3. 尝试 `localStorage.clear(); location.reload();` 清掉过期 token
4. 若仍不行，强制刷新（Ctrl+Shift+R / Cmd+Shift+R）

### Q3: 登录后报 401？
检查 `backend/.env` 或 `app/config.py` 中的 `JWT_SECRET_KEY` 是否与登录时一致。重启后端会清掉旧 token。

### Q4: AI 智能体调用失败？
在 `backend/.env` 中设置：
```bash
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### Q5: Neo4j 启动很慢？
Neo4j 首次启动需要 1-3 分钟初始化，查看 `docker logs ai4edu-neo4j` 确认进度。

### Q6: Celery 任务没跑起来？
```bash
docker logs ai4edu-celery-worker
docker logs ai4edu-celery-beat
# 确认 Redis 正常运行（Celery 依赖）
```

### Q7: 数据库重置后还是有问题？
```bash
# 硬重置
cd deploy
docker compose down -v
docker compose up -d --build
# 重新执行 seed
docker exec -it ai4edu-backend python scripts/seed_data.py
docker exec -it ai4edu-backend python scripts/seed_notes_resources.py
```

### Q8: 队友怎么访问我本地的服务？
两种方式：
1. **同一局域网**：直接用 `http://你的IP:5173`（前端）/ `:8000`（API）
2. **跨网络**：用 cloudflared 隧道
   ```bash
   start-tunnel.bat   # Windows
   # 复制输出的 https://xxxx.trycloudflare.com 发给队友
   ```

---

## 📞 协作联系

- 仓库地址：https://github.com/CAG1218/ai4edu
- 遇到问题先看 FAQ、搜 Issues
- 找不到答案 → 提 Issue / 群里 @主理人

---

> **TL;DR**：装 Docker + Node 22 + Python 3.11 → `cd deploy && docker compose up -d` → 访问 http://localhost:3000 → 拉分支开发新功能 → 提 PR。
