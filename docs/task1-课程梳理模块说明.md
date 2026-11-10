# 任务1 · 课程梳理模块说明

> 对应赛题「任务 1：理解学科 — 学习内容与要求梳理」
> 依据课程标准及配套材料，梳理指定范围内的主要学习内容、对应要求，以及对理解和安排学习有帮助的必要联系。

---

## 1. 设计思路

本模块把任务 1 做成平台的一个**能力**，而不是一份静态文档：

```
用户输入想学的课程（如"初中数学七年级上册"）
        │
        ▼
┌─────────────────────────────┐
│ 联网检索课程材料              │  duckduckgo-search，多源摘要
│ （可关闭，失败自动降级）        │
└─────────────────────────────┘
        │ 检索结果 + 权威课标出处
        ▼
┌─────────────────────────────┐
│ LLM 课程专家梳理              │  多模型路由（DeepSeek/通义/混元，自动降级）
│ 提示词硬性约束：               │
│  · 范围清楚（学段/教材/章节）   │
│  · 要求用课标行为动词表述       │
│  · 必要联系标注前置/相关/跨学科  │
│  · 材料出处必须真实可查        │
└─────────────────────────────┘
        │ 结构化 JSON
        ▼
┌─────────────────────────────┐
│ 离线知识包引擎（无 Key 兜底）   │  内置 14 个知识包，按课程/学段/范围匹配
│ · 范围边界显式列出（含/不含）   │  产出结构与 LLM 输出完全一致
│ · 出处固定为课标 + 教材 + MOOC  │  标记 is_sample，界面明确提示
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 持久化 + 三格式导出            │  JSON / Markdown / Word(.docx)
└─────────────────────────────┘
        │
        ▼
供后续学情分析与学习建议模块消费
（outline JSON 与知识图谱模块的
 知识点/认知水平/前置关系字段对齐）
```

**满足赛题要求的方式**

| 赛题要求 | 模块实现 |
|---------|---------|
| 学习内容与要求清单 | 每个单元给出内容主题、说明、课标要求句、要求水平（了解/理解/掌握/运用/经历/体验/感悟）、认知水平（记忆~创造）、建议课时 |
| 必要联系 | `connections` 数组，标注 前置(prerequisite)/相关(related)/跨学科(cross_subject) 及说明，字段与知识图谱模块的边类型对齐 |
| 材料出处 | `sources` 数组：课程标准（教育部官方链接）/教材/考试大纲/网络材料，每条注明用途；联网检索到的材料自动并入 |
| 范围清楚 | `scope` 字段明确界定学段/教材版本/章节边界，界面顶部展示 |
| 表达准确、组织合理 | LLM 提示词硬性约束课标行为动词；三格式导出内容一致、结构统一 |
| 便于后续学情分析与学习建议 | JSON 结构化存储（`curriculum_outlines` 表），认知水平与知识点字段可直接映射到知识图谱与诊断模块 |

## 2. 使用方式

1. 登录后进入任意场景，侧边栏 → **课程梳理**（`/scene/{sceneType}/curriculum`）
2. 输入想学的课程（可选填学段/学科/范围限定），点「开始梳理」（约 30-90 秒）
3. 查看三个部分：学习内容与要求清单 → 必要联系 → 材料出处
4. 右上角导出 **Word / Markdown / JSON** 三种格式

## 3. API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/curriculum/outlines` | 生成大纲（`use_web_search` 可关，`fallback_sample=true` 时 LLM 不可用回退内置示例） |
| GET | `/api/v1/curriculum/outlines` | 我的梳理历史（分页） |
| GET | `/api/v1/curriculum/outlines/{id}` | 大纲详情 |
| GET | `/api/v1/curriculum/outlines/{id}/export?format=json\|md\|docx` | 三格式导出下载 |

## 4. 数据结构（outline JSON）

```jsonc
{
  "course": "课程名",
  "subject": "math",            // 学科ID，与知识图谱模块 SUBJECT_CATEGORIES 对齐
  "grade_level": "七年级",
  "scope": "范围边界说明（一段话，含课程、学段、单元数、内容数、课时）",
  "scope_included": ["第1单元 …（4 条）", "第2单元 …"],   // 明确覆盖什么
  "scope_excluded": ["不覆盖/仅作了解的内容"],            // 明确不覆盖什么
  "units": [                    // 学习内容与要求清单
    {
      "name": "单元名",
      "textbook_ref": "教材出处",
      "contents": [{
        "topic": "内容主题",
        "requirement": "课标要求表述",
        "requirement_level": "掌握",
        "cognitive_level": "apply",   // remember/understand/apply/analyze/evaluate/create
        "suggested_hours": 2
      }]
    }
  ],
  "connections": [{              // 必要联系
    "from_topic": "有理数",
    "to_topic": "有理数的运算",
    "link_type": "prerequisite", // prerequisite/related/cross_subject
    "description": "为什么先学它"
  }],
  "sources": [{                  // 材料出处
    "title": "义务教育数学课程标准（2022年版）",
    "url": "http://www.moe.gov.cn/...",
    "source_type": "curriculum_standard",
    "usage": "作为要求表述依据"
  }]
}
```

内置示例见 `backend/app/data/sample_outline_math_7a.json`（初中数学七上，5 单元 / 18 条内容 / 8 条联系 / 3 个出处）。

## 5. 环境依赖

| 依赖 | 缺失时的行为 |
|------|------------|
| LLM API Key（`DEEPSEEK_API_KEY` / `QWEN_API_KEY` / `HUNYUAN_API_KEY` 任一，写在 `backend/.env`） | 自动降级为**离线知识包引擎**（不再报错）：匹配到内置包即产出完整大纲，并在界面标注「离线知识包，未调用大模型」；未匹配才返回 503 并给出可用课程清单 |
| `duckduckgo-search`（已加入 requirements.txt） | 跳过联网检索，LLM 依据权威课标知识梳理，材料出处仍给官方链接 |
| `python-docx`（requirements.txt 已有） | 仅影响 Word 导出，其余格式不受影响 |

## 6. 文件清单

**后端**
- `app/models/curriculum.py` — CurriculumOutline ORM
- `app/schemas/curriculum.py` — 大纲数据契约
- `app/services/curriculum_service.py` — 检索/梳理/导出核心服务
- `app/api/v1/curriculum.py` — 4 个端点
- `migrations/versions/f6b7c8d9e401_add_curriculum_outlines.py` — 建表迁移
- `app/data/sample_outline_math_7a.json` — 内置示例大纲（初中数学七上）
- `app/data/curriculum_packs.json` — 内置知识包（14 个课程/学科框架，离线梳理依据）
- `migrations/versions/b2c3d4e5f6a7_backfill_user_tenant.py` — 历史用户租户回填（修复 500，见第 9 节）

**前端**
- `src/services/curriculum.ts` — API 封装 + 类型
- `src/views/curriculum/CurriculumOutlineView.vue` — 课程梳理页面
- `src/router/routes/scene-routes.ts` — 路由注册
- `src/components/layout/Sidebar.vue` — 侧边栏入口

## 7. 本地实测记录（2026-11-09，Docker 全栈）

在 Windows 11 + Docker Desktop 环境按 README「方式 A」完整跑通，实测结果：

| 检查项 | 结果 |
|---|---|
| 10 个容器 | 全部 Up，其中 postgres / neo4j / redis / minio / elasticsearch / clickhouse 为 healthy |
| 数据库迁移 | `alembic upgrade head` 通过 6 个版本，含本模块的 `f6b7c8d9e401`（curriculum_outlines） |
| 默认账号登录 | `admin@ai4edu.com / admin123` → 200，返回 access_token |
| 生成大纲（`fallback_sample=true`，无 LLM Key） | 200，0.03s 返回：5 单元 / 18 条内容 / 8 条联系 / 3 个出处，落库 id=1 |
| JSON 导出 | 200，11,862 B |
| Markdown 导出 | 200，8,235 B，标题/范围/单元表格/联系/出处齐全 |
| Word 导出 | 200，40,198 B，ZIP 头 `PK` 校验为合法 docx |
| 前端经 nginx（80 口）代理调用 | 列表与导出均 200，`/api/v1` 代理链路正常 |
| 知识图谱 | 11 个 KnowledgeNode / 13 条关系，`/graphs/subjects/math/graph` 返回 7 节点 12 链接 |

配置 LLM Key 后，同一接口会走「联网检索 + 大模型梳理」的真实链路（首次约 30~90 秒）。

## 8. 离线知识包引擎（无大模型 Key 也能完整交付）

`backend/app/data/curriculum_packs.json` 内置 14 个知识包，结构与大模型输出的 JSON 完全一致（单元 / 内容要求 / 必要联系 / 材料出处），
因此**离线结果与在线结果走同一套渲染、导出、入库与学情消费链路**，只是内容来源不同。

| 类型 | 知识包 | 规模（单元 / 内容 / 联系 / 出处） |
|---|---|---|
| 专门课程 | 数据结构（含「二叉树」重点范围标注） | 7 / 35 / 12 / 4 |
| 专门课程 | 高等数学（微积分） | 7 / 25 / 8 / 3 |
| 专门课程 | 线性代数 | 5 / 13 / 7 / 3 |
| 专门课程 | 大学物理 | 6 / 18 / 9 / 3 |
| 专门课程 | 计算机网络 | 5 / 14 / 6 / 3 |
| 示例课程 | 初中数学七年级上册（人教版） | 5 / 18 / 8 / 3 |
| 学科框架 | 中学数学 / 中学物理 | 3 / 9 |
| 学科框架 | 化学 / 生物学 / 语文 / 英语 / 历史 / 地理 / 思想政治 | 3–4 单元 / 9–12 条 |

匹配规则（`CurriculumService._score_pack`）：

1. 课程名命中 +8，关键词命中 +2~3，学科命中 +4，年级命中 +1；
2. **学段互斥惩罚 −8**：用户输入「初中物理」时《大学物理》不会命中，改由《中学物理》框架承接，避免超纲；
3. 得分 < 3 视为未匹配，返回 503 并列出可用课程，绝不硬套无关内容；
4. 命中后在 `scope` 中写明课程、学段、单元数、内容数、课时，以及「限定重点」落在哪些单元/条目；
   `scope_included` 列出覆盖的单元，`scope_excluded` 列出不覆盖或仅作了解的内容 → 直接对应赛题「范围清楚」。

> 提示：配置任意一家 API Key 后，同一入口会自动切换为「联网检索 + 大模型梳理」，产出会细化到具体教材版本与章节。

## 9. 2026-11-10 修复记录：500 服务器内部错误

**现象**：课程梳理页面点击「开始梳理」后顶部提示「服务器内部错误」，页面底部 `Request failed with status code 500`。

**根因**：自注册用户（如 `3511415754@qq.com`）注册时未写 `users.tenant_id`，接口里 `current_user.tenant_id or 0` 把 `NULL` 兜底成 `0`，
而 `curriculum_outlines.tenant_id` 有外键指向 `tenants(id)`，插入 `tenant_id=0` 直接触发

```
asyncpg.exceptions.ForeignKeyViolationError:
insert or update on table "curriculum_outlines" violates foreign key constraint
DETAIL: Key (tenant_id)=(0) is not present in table "tenants".
```

**修复（三层）**：

| 层次 | 改动 | 作用 |
|---|---|---|
| 认证层 | `app/dependencies.py::get_current_user` 发现 `user.tenant_id is None` 时自动归属默认租户（`MIN(tenants.id)`）并落库 | 一次性修好所有 `tenant_id or 0` 的模块（笔记/课堂/诊断/导出等 19 张表同理） |
| 注册流程 | `app/services/auth_service.py::register` 创建用户时写入默认租户 | 新用户不再产生脏数据 |
| 数据层 | 迁移 `b2c3d4e5f6a7_backfill_user_tenant.py` 回填历史 NULL 用户，并在 `tenants` 为空时补建默认租户 | 老数据一次性修正，可随迁移复制到任何环境 |

**复测（同一输入：数据结构 / 大二 / 范围「二叉树」/ 联网检索开启）**：

| 检查项 | 修复前 | 修复后 |
|---|---|---|
| POST `/curriculum/outlines` | 500（外键冲突） | 200，7 单元 / 35 条内容 / 12 条联系 / 4 条出处 |
| 页面提示 | 服务器内部错误 | 正常展示大纲 + 成果概览 + 范围边界 |
| 生成耗时 | — | 0.9 s（离线知识包，联网检索失败自动跳过） |
| Markdown 导出 | — | 200，15,692 B |
| Word 导出 | — | 200，43,603 B（`PK` 头校验通过） |
| 其他课程 | — | 高等数学 / 线性代数 / 大学物理 / 初中数学七上 / 中学物理 / 中学数学 / 化学 / 生物 / 语文 / 英语 / 历史 / 地理 / 政治 / 计算机网络 全部 200 |

样例成果见 `docs/samples/`：`数据结构(二叉树)_学习内容与要求梳理.{md,docx,json}`、`初中数学七上_学习内容与要求梳理.md`。
