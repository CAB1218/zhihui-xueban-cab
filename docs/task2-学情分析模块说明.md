# 学情分析模块说明（理解学生 — 学生学习情况分析）

> 面向赛题「任务 2」的实现说明。本文只讲这一块怎么做的、为什么这么判、数据从哪来、结论怎么追。

## 1. 赛题要求与实现的对应关系

| 赛题原文 | 本模块的实现 |
|---|---|
| 对模拟学情数据进行必要的整理和质量检查 | `POST` 不走前端，统一在 `LearningAnalysisService.check_quality()` 做流水线清洗 |
| 说明缺失、异常及重复记录等情况的处理方式 | 每类问题输出「问题描述 + 条数 + 示例记录 ID + 处理方式 + 处理前后条数」，界面与导出报告都有 |
| 形成个体与群体两个层面的学习情况摘要 | `individual/{id}` 与 `group` 两个端点，前端两个 Tab |
| 成果应反映已有学习表现 | 所有指标都由真实记录聚合而来，不做估算填充 |
| 指出需要巩固的内容、值得关注的差异及共性问题 | 个体输出 `needs_consolidation`；群体输出 `common_weak_points`（≥50% 学生同时薄弱）与 `differences` |
| 提供相应记录或统计依据 | 每个知识点结论附 `evidence_record_ids`；每条统计结论附 `evidence_text` |
| 分析维度应与实际数据相匹配 | `dimension_check` 显式列出每个维度的数据可用率与是否采用 |
| 对信息不足、尚不能确定的情况应作出说明 | `insufficient_evidence` + `data_notes`，界面单独用一块卡片展示 |
| 避免将缺少记录直接解释为未掌握 | 样本 < 3 次一律标「证据不足，尚不能判断」；群体横向比较只纳入「至少一个知识点样本达标」的学生 |

## 2. 数据来源与模拟数据设计

现有系统里的真实学情记录接近空白（`diagnoses` 0 条、`flash_cards` 0 条、`course_enrollments` 0 条），因此按要求使用**模拟数据**，并在界面与报告首页明确标注「模拟数据」。

生成脚本：`backend/scripts/seed_learning_records.py`

| 维度 | 设计 |
|---|---|
| 学生 | 10 名模拟学生 + 1 名验收学生，覆盖「学霸 / 中间 / 偏科 / 后进 / 少样本」五类画像 |
| 课程 | 数据结构（8 个知识点）、高等数学（6 个知识点） |
| 记录量 | 469 条干净记录 + 21 条刻意注入的问题记录 = 490 条 |
| 时间跨度 | 最近 60 天 |

刻意注入的质量问题（模拟真实采集链路的常见故障）：

| 类别 | 注入内容 | 条数 |
|---|---|---|
| 缺失 | 分值为空（仍保留对错标记） | 8 |
| 缺失 | 分值与对错同时为空 | 7 |
| 缺失 | 知识点为空 | 10 |
| 缺失 | 作答耗时为空 | 5 |
| 异常 | 得分超过满分 | 5 |
| 异常 | 耗时离谱（86400 ~ 999999 秒） | 6 |
| 异常 | 耗时为负 | 3 |
| 异常 | 记录时间在未来（2027 年） | 2 |
| 重复 | 业务字段完全相同的重复上报 | 16 |
| 重复 | 同人同知识点同分钟内的二次提交 | 5 |

学生画像的设计目的：

- **郑可**：8 次作答分散在 8 个知识点，每个点 1 次 → 用来验证「记录少 ≠ 没学会」
- **孙悦**：34 次作答、正确率 41% → 真正的后进生，结论有样本支撑
- **王雨桐**：总量 63%，但树与二叉树极强、排序极弱 → 用来验证「偏科」能被识别
- **刘欣然 / 周景行**：整体较好 → 作为对照

## 3. 质量检查流水线

处理顺序固定为 **去重 → 异常 → 缺失**，每步记录 before/after，保证数字可对账。

### 3.1 重复

| 子类 | 判定 | 处理 |
|---|---|---|
| 完全重复 | 学生 + 课程 + 知识点 + 记录类型 + 得分 + 满分 + 耗时 + 时间 全部相同 | 保留 ID 最小的一条，其余剔除 |
| 近似重复 | 同学生 + 同知识点 + 同一分钟，但得分不同 | 保留得分最高的一条（视作订正后结果），其余合并 |

> 为什么不全按「保留最新」：同一分钟内无法判断哪条更晚；保留最高分更符合「订正后取最终结果」的教学语义，也避免重复计入练习量。

### 3.2 异常

| 子类 | 判定 | 处理 | 是否影响正确率 |
|---|---|---|---|
| 记录时间在未来 | `recorded_at > now()` | 整条剔除 | 是（不进入分析） |
| 得分超过满分 | `score > max_score` | 按满分截断 | 否（修正后保留） |
| 耗时异常 | `< 0` 或 `> 6 小时` | 耗时字段置空 | 否（保留得分与对错） |

> 设计取舍：分数超满分通常是满分值没同步（比如加分题），整条丢掉会丢真实作答信息，所以截断保留；耗时异常则只影响时长维度，没必要牵连正确率。

### 3.3 缺失

| 子类 | 判定 | 处理 |
|---|---|---|
| 结果完全缺失 | `score` 与 `is_correct` 均为空 | 剔除，不进任何正确率分母 |
| 分值缺失 | `score` 空但 `is_correct` 有值 | 保留，参与正确率，不参与得分率 |
| 知识点缺失 | `knowledge_point` 空 | 保留在总体统计，知识点维度分析时排除并声明 |
| 耗时缺失 | `duration_seconds` 空 | 保留，时长统计时排除 |

### 3.4 为什么各类问题条数之和可能大于总剔除数

一条记录可能同时命中多类问题（既重复又分数异常）。报告里明确写了这一点，并给出每步的 before/after 让读者自行对账：

```
完全重复去重      347 → 331  (-16)
近似重复合并      331 → 329  (-2)
剔除未来时间      329 → 328  (-1)
剔除结果全缺      328 → 321  (-7)
────────────────────────────────
原始 347 → 有效 321，共剔除 26 条
```

## 4. 判定口径

口径全部在接口响应里以 `thresholds` 字段返回，界面和报告都会显示，不做黑箱。

| 参数 | 取值 | 含义 |
|---|---|---|
| `MIN_ATTEMPTS_FOR_JUDGEMENT` | 3 | 同一知识点作答少于 3 次，不下掌握/未掌握结论 |
| `ACC_GOOD` | 0.80 | 正确率 ≥ 80% 记为「掌握良好」 |
| `ACC_WEAK` | 0.60 | 正确率 < 60% 记为「需巩固」 |
| 中间区间 | 60% ~ 80% | 记为「基本掌握、建议适度巩固」，不夸大也不贬低 |
| `COMMON_WEAK_RATIO` | 0.50 | ≥ 50% 学生在该点薄弱，才认定为群体共性问题 |

### 关于「避免将缺少记录解释为未掌握」

这是本模块最容易被做错的地方，实现上分三层防护：

1. **单知识点层**：作答 < 3 次 → `status = insufficient`，文案是「证据不足，尚不能判断」，单独归到 `insufficient_evidence`，不进入「需巩固」列表。
2. **学生层**：横向排名只纳入「至少有一个知识点样本达标」的学生。郑可 8 次作答分散在 8 个点，虽然总量超过 6 次，仍被判为不可靠，只出现在「样本不足」提示里。
3. **文案层**：说明文字明确写「这不代表其学习落后，而是数据不足以判断」。

## 5. 输出结构

### 个体（`GET /learning-analysis/individual/{student_id}`）

```jsonc
{
  "overall": { "attempts": 34, "accuracy": 0.4118, "accuracy_basis": "基于 34 条可判断对错的记录计算" },
  "knowledge_points": [
    {
      "knowledge_point": "查找", "attempts": 5, "correct_count": 1, "accuracy": 0.2,
      "status": "needs_work", "status_label": "需巩固",
      "evidence_record_ids": [188, 205, 233, 260, 301],
      "evidence_text": "5 次作答中 1 次正确，正确率 20.0%"
    }
  ],
  "needs_consolidation": [ /* 需巩固 */ ],
  "fair_areas": [ /* 基本掌握 */ ],
  "strengths": [ /* 掌握良好 */ ],
  "insufficient_evidence": [ /* 证据不足 */ ],
  "data_notes": [ "… 样本不足以判断掌握情况，已在表中标注为「证据不足」，这不等于未掌握。" ],
  "thresholds": { "min_attempts": 3, "acc_good": 0.8, "acc_weak": 0.6 }
}
```

### 群体（`GET /learning-analysis/group?course_id=`）

```jsonc
{
  "cohort": { "students_total": 11, "students_judged": 11, "students_reliable": 10, "students_sparse": 1, "total_attempts": 321 },
  "overall": { "accuracy": 0.6636 },
  "common_weak_points": [
    { "knowledge_point": "排序", "accuracy": 0.54, "weak_students": 6, "students_practiced": 10,
      "weak_ratio": 0.6, "is_common_weak": true,
      "evidence_text": "10 名有作答记录的学生中，6 名在该知识点上正确率低于 60%，整体正确率 54.0%" }
  ],
  "differences": { "accuracy": { "min": 0.4118, "max": 0.8485, "gap": 0.4367, "std": 0.128,
                    "compared_students": 10, "evidence_text": "在 10 名作答量充足的学生中…" } },
  "notable_cases": [
    { "type": "low", "student_name": "孙悦", "note": "正确率 41.2%，低于班级均值 66.4% 约 25 个百分点，有 34 次作答作为依据，结论可靠" },
    { "type": "insufficient", "student_name": "郑可", "note": "共 8 次作答，分散在 8 个知识点上，没有单个知识点达到 3 次的判断门槛，暂不能评价其掌握水平" }
  ],
  "dimension_check": [
    { "dimension": "知识点掌握（正确率）", "available_ratio": 0.98, "usable": true, "note": "本次分析的主维度" },
    { "dimension": "题目难度", "available_ratio": 0.0, "usable": false, "note": "现有记录未采集难度字段，本次不做难度分层分析，避免臆造" },
    { "dimension": "错因归类", "available_ratio": 0.0, "usable": false, "note": "记录里没有错因标注，只能说明「哪个点偏弱」，不能说明「为什么错」" }
  ]
}
```

## 6. 接口清单

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/learning-analysis/overview` | 记录规模、覆盖学生、整体正确率、时间范围 |
| GET | `/api/v1/learning-analysis/quality` | 质量问题明细 + 处理流程 + 说明 |
| GET | `/api/v1/learning-analysis/students` | 有记录的学生列表（含可判断作答数） |
| GET | `/api/v1/learning-analysis/individual/{student_id}` | 个体摘要 |
| GET | `/api/v1/learning-analysis/group` | 群体摘要 |
| GET | `/api/v1/learning-analysis/export` | 导出 `format=md\|docx`，`kind=group\|individual` |

## 7. 文件清单

| 文件 | 作用 |
|---|---|
| `backend/app/models/learning_record.py` | 学情记录 ORM 模型 |
| `backend/migrations/versions/c7d8e9f0a1b2_add_learning_records.py` | 建表迁移 |
| `backend/scripts/seed_learning_records.py` | 模拟数据生成（含质量问题注入） |
| `backend/app/services/learning_analysis_service.py` | 质量检查 / 个体摘要 / 群体摘要 / 报告渲染 |
| `backend/app/api/v1/learning_analysis.py` | 6 个接口 |
| `frontend/src/services/learningAnalysis.ts` | 前端接口封装与类型定义 |
| `frontend/src/views/analysis/LearningAnalysisView.vue` | 学情分析页面 |

## 8. 实测记录（2026-11-10）

数据：数据结构课程，原始 347 条，有效 321 条，剔除 26 条，11 名学生，整体正确率 66.4%。

| 检查项 | 结果 |
|---|---|
| 质量检查数字自洽 | 347 → 331 → 329 → 328 → 321，每步对账一致 |
| 共性问题识别 | 排序 54.0%（6/10 薄弱）、图的遍历 46.2%（6/11 薄弱） |
| 差异分析 | 10 名样本充足学生中，最高 84.9%、最低 41.2%，相差 43.7 个百分点，标准差 0.128 |
| 少样本保护 | 郑可 8 次作答分散 8 个知识点，全部标「证据不足」，未进入排名 |
| 个体判定分档 | 孙悦：6 项需巩固 / 1 项基本掌握 / 1 项掌握良好；周景行：1 项需巩固 / 3 项基本掌握 / 4 项掌握良好 |
| 维度匹配 | 知识点 98%、耗时 97% 采用；难度 0%、错因 0% 明确声明不采用 |
| 导出 | 班级报告 MD 5,429 B / DOCX 39,191 B；个人报告 MD 3,006 B / DOCX 38,440 B，DOCX 均为合法 `PK` 头 |
