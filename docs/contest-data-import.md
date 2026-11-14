# 赛题模拟学情数据导入说明

> 用赛题提供的模拟学情数据替换平台里随机生成的演示数据，让「学情分析 / 课程梳理 / 资源管理 / 智能体」都跑在真实赛题数据上。
> 导入脚本：`backend/scripts/import_contest_data.py`　模型：`backend/app/models/contest.py`　迁移：`j1f2a3b4c5d6`

---

## 一、数据来源

赛题资料（七年级数学，主题 T01 代数式与整式运算 / T02 方程与方程组 / T03 不等式与不等式组）：

| 文件 | 规模 | 去向 |
|---|---|---|
| `模拟学情数据/模拟学生.csv` | 40 名学生（D01—D40，DC01/DC02 两班） | `users`（班级存 `preferences.class_code`）+ `course_enrollments` |
| `模拟学情数据/作答记录.csv` | 806 条作答（含修订版本、评分点得分） | `learning_records`（原始字段全部保留在 `raw_payload`） |
| `模拟学情数据/课程要求.csv` | 3 主题 / 9 条观察指标 | `contest_course_requirements` + 生成一份 `curriculum_outlines` |
| `模拟学情数据/测验节点.csv` | 2 个节点（N01 2026-01-20 / N02 2026-06-17） | `contest_exam_nodes` |
| `模拟学情数据/题目与材料.csv` | 54 题 + 3 学习卡 + 8 教材条目 | `contest_materials` |
| `课程标准_2022.pdf`、`B01—B08_相关资料切片.pdf` | 9 个 PDF | MinIO（`contest/` 前缀）+ `resources` |

## 二、字段映射要点

- **知识点粒度用「观察指标」**：`learning_records.knowledge_point` 取 9 条观察指标文本（如「识别同类项、去括号并化简」），比 3 个主题更适合做掌握度分析；主题/指标编号/材料编号等都写进 `raw_payload`。
- **`is_correct` 三态**：满分 → `True`，0 分 → `False`，部分得分（解答题）→ `NULL`，避免把「拿了 1/3 分」误判为对或错。
- **赛题无耗时字段**：`duration_seconds` 统一为 `NULL`，质量检查会如实报「作答耗时为空」，属数据本身缺失，不是导入丢失。
- **重复记录原样保留**：同一「作答事件编号」的多个修订版本全部入库，由分析服务的去重逻辑处理，保证「可回溯」。
- **`is_simulated=True`**：赛题数据本身是模拟数据，如实标注来源。

## 三、导入步骤

```bash
# 1. 数据放进容器（CSV 目录 + 9 个 PDF）
docker exec ai4edu-backend mkdir -p /app/data/contest
docker cp 'C:\Users\<你>\Desktop\模拟学情数据' ai4edu-backend:/app/data/contest/
docker cp 'C:\Users\<你>\Desktop\课程标准_2022.pdf' ai4edu-backend:/app/data/contest/
docker cp 'C:\Users\<你>\Desktop\B01_相关资料切片.pdf' ai4edu-backend:/app/data/contest/   # B02—B08 同理

# 2. 建表（新增 3 张赛题支撑表）
docker exec ai4edu-backend alembic upgrade head

# 3. 导入（幂等，可重复执行）
docker exec ai4edu-backend python scripts/import_contest_data.py
```

脚本会先清理旧数据再重建，因此重复执行不会产生重复行：

1. 删除 `learning_records.is_simulated = True` 的旧随机记录
2. 删除旧演示学生（`chenjiahe@…` 等 10 个）及其在业务表中的引用
3. 重建课程「七年级数学」、40 名学生、选课关系
4. 重建 `contest_*` 三张表与课程大纲
5. 上传 9 个 PDF 到 MinIO 并登记 `resources`

## 四、导入结果（2026-11-14 实测）

| 指标 | 结果 |
|---|---|
| 学情记录 | 806 条（旧 490 条随机数据已删除） |
| 学生 | 40 人（DC01 21 人 / DC02 19 人），全部选入「七年级数学」 |
| 观察指标覆盖 | 9 个知识点，每个 29—193 条作答 |
| 课程要求 / 测验节点 / 题目材料 | 9 / 2 / 65 条 |
| 资源 | 9 个 PDF（课程标准 38.3 MB + 8 个教材切片） |
| 旧演示学生 | 0（已清空） |

**数据质量检查结果**（学情分析页可直接看到，正是赛题要求说明的部分）：

- 原始 806 → 有效 795（剔除 11 条）
- 重复 1 条：同一知识点同一时间重复提交 → 合并保留最高分
- 异常 2 条：得分超过满分 → 按满分截断并保留原值
- 缺失 805 条：作答耗时为空的记录 → 保留但不计入耗时分析

## 五、配套前端修复

赛题数据替换后暴露了两个问题，已一并修好：

1. **学情分析页默认落在空课程上**：原来硬编码选「数据结构」，该课程已无数据 → 显示 0 条并弹 404。
   现在 `/teachers/courses` 返回 `record_count`，前端默认选「有记录最多」的课程。
2. **「该课程暂无记录」被当成错误弹窗**：`group` / `individual` 的 404 属正常空态。
   axios 拦截器新增 `silent` 配置，这两个接口静默失败，由页面渲染空状态。

## 六、当前限制

| 项 | 状态 | 说明 |
|---|---|---|
| PDF 向量检索（RAG） | 未启用 | `Embedder` 依赖 OpenAI Embedding Key，当前未配置；PDF 已入库可下载查看，配好 Key 后可再跑索引 |
| 智能体对话读数据 | 受限于大模型 | DeepSeek 账户余额为 0，对话走本地规则引擎（`demo-rule-engine`），不会读取库里的学情；充值后在「模型配置」点「测试连接」即可让智能体基于真实数据作答 |
| 班级维度对比 | 数据已存 | DC01/DC02 存在 `users.preferences.class_code`，分析服务暂按课程维度聚合，班级对比可在案例文档中按此字段筛选 |
| 赛题原始文件 | 未入库 | CSV/PDF 属赛题资料（赛规限定仅用于本赛题），不提交到代码仓库；按第三节步骤从本地目录导入即可 |
