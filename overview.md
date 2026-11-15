# 智慧学伴 项目交付总览

## 最新模块：学生成长档案（2026-07-09）

### TL;DR
完成学生成长档案模块开发：教师评价 CRUD + 学生成长档案查看 + 自动聚合时间线 + 概览仪表盘，17 个文件 3997 行代码，已推送 GitHub 并部署到阿里云 ECS。云端 API 端到端验证全部通过。

### 交付概览

| 指标 | 数值 |
|------|------|
| 交付状态 | ✅ 全部完成 |
| 新增文件 | 12 |
| 修改文件 | 5 |
| 代码行数 | +3997 / -34 |
| Git 提交 | `153fb8d` + `ba5b947` + `456cbcb` + `62a0967` + `4594e44` |
| 分支 | `陈安国的代码——学生成长档案` |
| 云端部署 | ✅ 镜像重建 + 容器切换 + 迁移执行 + API 验证 + 前端 403 修复 + 邀请码移除 |

### 功能实现详情

#### 1. 教师评价与学习建议（P0）
- 教师给学生写评价（文字+评分1-5星+评价类型）和学习建议
- 评价类型：overall/academic/attitude/improvement
- 支持关联课程，支持可见性控制
- 新增 `StudentEvaluation` 数据模型 + Alembic 迁移

#### 2. 学生成长档案查看（P0）
- 学生查看自己的成长档案（个人信息+仪表盘+时间线+教师评价）
- 教师查看学生档案（带写评价/编辑/删除功能）
- 双视角路由：学生端 `/scene/:sceneType/growth-profile` + 教师端 `/teacher/students/:studentId/growth-profile`

#### 3. 自动聚合成长时间线（P0）
- 从 8 个数据源并行聚合学习行为：AI对话/学习诊断/笔记/复习卡片/教师评价/课程选课/资源收藏/课堂参与
- 使用 `asyncio.gather` 并行查询，按时间倒序排列，支持分页和筛选

#### 4. 成长档案概览仪表盘（P0）
- 8 张统计卡片（AI对话数/诊断次数/笔记数/卡片数/课程数/评价数/收藏数/课堂数）
- 近 7 天学习活跃度柱状图（ECharts）
- 学科分布饼图
- 最近教师评价列表

### 文件清单

**后端（7 个文件）**：
- `backend/app/models/evaluation.py` — StudentEvaluation ORM 模型
- `backend/app/schemas/growth.py` — Pydantic schemas
- `backend/app/services/growth_service.py` — 聚合查询服务（评价CRUD+时间线+仪表盘）
- `backend/app/api/v1/growth.py` — 7 个 API 端点
- `backend/migrations/versions/d4f5a6b7c802_add_student_evaluations.py` — Alembic 迁移
- `backend/app/models/__init__.py` — [修改] 注册导入
- `backend/app/api/v1/router.py` — [修改] 注册路由

**前端（10 个文件）**：
- `frontend/src/services/growth.ts` — API 服务 + TypeScript 类型
- `frontend/src/stores/growth.ts` — Pinia store
- `frontend/src/views/growth/GrowthProfileView.vue` — 主页面
- `frontend/src/views/growth/components/GrowthDashboard.vue` — 仪表盘组件
- `frontend/src/views/growth/components/GrowthTimeline.vue` — 时间线组件
- `frontend/src/views/growth/components/TeacherEvaluationCard.vue` — 评价卡片
- `frontend/src/views/growth/components/EvaluationForm.vue` — 评价表单
- `frontend/src/router/routes/scene-routes.ts` — [修改] 学生端路由
- `frontend/src/router/routes/teacher-routes.ts` — [修改] 教师端路由
- `frontend/src/components/layout/Sidebar.vue` — [修改] 侧边栏菜单

**文档（2 个文件）**：
- `docs/prd-student-growth-profile.md` — PRD 文档
- `docs/architecture-student-growth-profile.md` — 架构设计文档

### SOP 流程
```
产品经理（许清楚）→ PRD
    ↓
架构师（高见远）→ 架构设计 + 任务分解（20个任务）
    ↓
工程师（寇豆码）→ 后端7文件 + 前端10文件（并行实现）
    ↓
主理人（齐活林）→ 部署云端 + Git commit + push GitHub
```

### 数据库变更
- **新增 1 表**：`student_evaluations`（教师评价表）
- **迁移文件**：`d4f5a6b7c802_add_student_evaluations.py`
- **迁移链**：`c8e2a4f7b901` → `d4f5a6b7c802`

### 云端验证结果
- ✅ Backend 健康检查通过
- ✅ `student_evaluations` 表创建成功
- ✅ Alembic 版本：`d4f5a6b7c802 (head)`
- ✅ Dashboard API：返回 8 个统计卡片 + 7 天活跃度 + 学科分布
- ✅ Timeline API：返回 AI 对话历史（24 条记录，8 源聚合）
- ✅ Evaluations CRUD：创建/列表/详情全部正常
- ✅ 修复 `super_admin` 权限问题（`require_role` 添加 `super_admin` 角色）
- ✅ 修复前端 403 Forbidden：`ai4edu-frontend` 容器改用 nginx:1.25-alpine + bind mount `frontend/dist` + 端口 80:80
- ✅ 修复超管点击侧边栏成长档案无反应：路由守卫放行 `super_admin`，统一 `teacher-routes`/`admin-routes` 使用 `allowedRoles`
- ✅ 移除教师注册邀请码校验：前端表单移除邀请码输入框，后端移除校验逻辑，教师注册无需邀请码即可成功

---

## 前序模块：AI 智能体中心 v2

## TL;DR
完成 AI 智能体中心 4 项增强能力（板书/录播 OCR/ASR 提取、多租户配额计量、对话导出 PDF/MD、模型负载均衡），42 个文件 8384 行代码，179 个测试全部通过，已推送 GitHub。

## 交付概览

| 指标 | 数值 |
|------|------|
| 交付状态 | ✅ 全部完成 |
| 测试通过率 | 179/179 (100%) |
| 已知问题数 | 0 |
| 新增文件 | 26 |
| 修改文件 | 16 |
| 代码行数 | +8384 / -238 |
| Git 提交 | `fddf28d` |
| 分支 | `陈安国的代码——AI智能体中心` |

## 4 项能力实现详情

### 1. 板书/录播自动 OCR/ASR 提取（P1）
- **架构**：Strategy + Factory 设计模式，多 provider 抽象层
- **降级链**：aliyun → tencent → mock（无 API Key 也能跑通）
- **异步处理**：Celery 任务队列（Redis broker）
- **关键文件**：
  - `backend/app/services/ocr_service.py` — OCR 多 provider
  - `backend/app/services/asr_service.py` — ASR 多 provider
  - `backend/app/tasks/extraction_tasks.py` — Celery 异步任务
  - `backend/app/api/v1/classroom.py` — 课堂记录 API
- **测试**：OCR 22 个 + ASR 20 个 = 42 个全部通过

### 2. 多租户模型配额计量（P2）
- **架构**：Redis 实时计数 + DB 持久化日志
- **计数策略**：日配额（TTL 25h）+ 月配额（TTL 35d）
- **关键文件**：
  - `backend/app/services/quota_manager.py` — QuotaManager 单例
  - `backend/app/models/usage.py` — LLMUsageLog + TenantQuota
  - `backend/app/api/v1/quota.py` — 配额管理 API
  - `frontend/src/views/admin/QuotaDashboard.vue` — 配额看板
- **测试**：7 个全部通过

### 3. 对话导出 PDF/Markdown（P2）
- **架构**：reportlab 纯 Python PDF 生成（无系统依赖），MinIO 预签名 URL
- **安全**：导出文件仅创建者可下载，30 分钟有效期
- **关键文件**：
  - `backend/app/services/agent_export_service.py` — 导出服务
  - `backend/app/tasks/export_tasks.py` — Celery 导出任务
  - `backend/app/api/v1/export.py` — 导出 API
  - `frontend/src/components/agent/ExportDialog.vue` — 导出对话框
- **测试**：7 个全部通过

### 4. 模型负载均衡（P2）
- **架构**：基于延迟/可用性的动态负载均衡
- **策略**：latency（默认按延迟排序）、weighted（按成功率加权随机）、sticky（优先 recommended_model）
- **健康指标**：指数移动平均（EMA）更新 avg_latency_ms 和 success_rate
- **关键改造**：
  - `backend/app/agents/llm_router.py` — 新增 tenant_id 配额检查 + 健康指标 + balancer 状态
  - `backend/app/tasks/health_check.py` — Celery beat 每 60s 探测
- **测试**：10 个全部通过

## 数据库变更
- **新增 3 表**：llm_usage_logs、tenant_quotas、agent_exports
- **修改 2 表**：classroom_records（加 file_url/provider/error_msg/updated_at）、teacher_methods（加 recommended_model）
- **迁移文件**：`backend/migrations/versions/c8e2a4f7b901_add_v2_models.py`

## 文档产出
- `docs/prd-ai-agent-center-v2.md` — 增量 PRD（用户故事 + 需求池 + UI 设计 + 流程图）
- `docs/architecture-ai-agent-center-v2.md` — 增量架构设计（10 项设计决策 + 5 个任务分解）
- `docs/class-diagram-v2.mermaid` — v2 类图
- `docs/sequence-diagram-v2.mermaid` — v2 时序图

## SOP 流程
```
产品经理（许清楚）→ PRD v2
    ↓
架构师（高见远）→ 架构设计 v2 + 任务分解
    ↓
工程师（寇豆码）→ 代码实现（42 文件，IS_PASS: YES）
    ↓
QA（严过关）→ 测试验证（179 passed）
    ↓
主理人（齐活林）→ Git commit + push GitHub
```

## 用户下一步建议
1. ~~**运行 Alembic 迁移**~~：✅ 已完成（本地 + 云端）
2. ~~**安装新依赖**~~：✅ 已完成
3. ~~**启动 Celery worker/beat**~~：✅ 已完成（本地进程 + Docker 容器）
4. ~~**重建后端 Docker 容器**~~：✅ 已完成（本地 + 阿里云 ECS）
5. **配置 OCR/ASR API Key**（可选）：设置 ALIYUN_OCR_API_KEY / TENCENT_OCR_SECRET_ID 等环境变量，无配置时自动降级为 mock
6. **访问云端服务**：
   - 前端：http://121.43.129.181
   - 后端 Swagger：http://121.43.129.181:8000/docs
7. **安全建议**：生产环境请修改默认密码、关闭 8000 端口公网访问或配置 HTTPS/鉴权

## 部署修复记录
- `schemas/classroom.py`：合并旧+新 schema（v2 覆盖了旧 ClassroomCreate 等类）
- `api/v1/classroom.py`：修复 `get_db_dep` 未定义 → 改用 `get_db` from `app.dependencies`
- `docker-compose.yml`：修复 celery 模块路径 `app.celery` → `app.core.celery_app` + 补全环境变量
- `.dockerignore`：排除 `celerybeat-schedule*` 文件
- 提交：`a521d1c`

## 当前运行状态
- **本地**：9 个 Docker 容器运行，Backend API http://localhost:8000，v2 API 已上线
- **阿里云 ECS**：10 个 Docker 容器运行（9 后端 + 1 Nginx 前端）
  - 前端网站：http://121.43.129.181 ✅ 已修复白屏（2026-07-04 重新构建 dist + 更新 Nginx 缓存头）
  - 后端 API：http://121.43.129.181:8000/docs
  - v2 API 端点已注册：/api/v1/agents/models/balancer、/api/v1/admin/quotas/status、/api/v1/admin/quotas/dashboard 等
  - Alembic 版本：`c8e2a4f7b901 (head)`
  - Celery 任务已注册：`process_board_ocr`, `process_video_asr`, `export_session_task`, `health_check_task`

## 云端部署修复记录
- `backend/Dockerfile`：添加阿里云镜像源（apt + PyPI）+ `ENV PYTHONPATH=/app`
  - 原因：阿里云 ECS 访问 Debian 官方源极慢；容器内 `alembic`/`celery` 找不到 `app` 模块
- `scripts/deploy_v2_cloud_full.py`：完整 Paramiko SFTP/SSH 部署脚本，含 Alembic `stamp + upgrade` 和验证
- 修复 Celery 镜像未重建问题：显式 `docker compose build --no-cache celery-worker celery-beat` 后再重建容器
- Alembic 云端迁移：`stamp 61a4199a88b0` → `upgrade head` → `c8e2a4f7b901`
- **前端白屏修复（2026-07-04）**：
  - 重新构建 `frontend/dist`（旧 dist 为 6 月 28 日，未包含 v2 视图）
  - 修复 `frontend/tsconfig.json`：移除对 `tsconfig.sw.json` 的 project reference
  - 修复 `frontend/vite.config.ts`：PWA 使用 `strategies: 'InjectManifest'` + `injectManifest: { swSrc, swDest }`
  - 更新 `deploy/nginx/conf.d/default.http.conf`：为 `location /`、`/registerSW.js`、`/sw.js` 添加 no-cache 头，避免 Service Worker 缓存旧 `index.html`
