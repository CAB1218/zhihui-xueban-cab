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
  "scope": "范围边界说明",
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
| LLM API Key（`DEEPSEEK_API_KEY` / `QWEN_API_KEY` / `HUNYUAN_API_KEY` 任一，写在 `backend/.env`） | 返回 503 并提示配置；请求带 `fallback_sample=true` 可查看内置示例 |
| `duckduckgo-search`（已加入 requirements.txt） | 跳过联网检索，LLM 依据权威课标知识梳理，材料出处仍给官方链接 |
| `python-docx`（requirements.txt 已有） | 仅影响 Word 导出，其余格式不受影响 |

## 6. 文件清单

**后端**
- `app/models/curriculum.py` — CurriculumOutline ORM
- `app/schemas/curriculum.py` — 大纲数据契约
- `app/services/curriculum_service.py` — 检索/梳理/导出核心服务
- `app/api/v1/curriculum.py` — 4 个端点
- `migrations/versions/f6b7c8d9e401_add_curriculum_outlines.py` — 建表迁移
- `app/data/sample_outline_math_7a.json` — 内置示例大纲

**前端**
- `src/services/curriculum.ts` — API 封装 + 类型
- `src/views/curriculum/CurriculumOutlineView.vue` — 课程梳理页面
- `src/router/routes/scene-routes.ts` — 路由注册
- `src/components/layout/Sidebar.vue` — 侧边栏入口
