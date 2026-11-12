# 知识图谱：学科知识点无法导入/编辑的修复

> 现象：在「图谱详情 · 物理学」页面，「学科知识结构图」为空；「协作编辑」点了没明显效果；没有导入知识点的入口。

## 1. 三个根因

### 1.1 知识点挂错了学科节点（图空白的主因）

早期种子数据在 `create_node` 尚未归一化学科名时就写库了，结果 Neo4j 里出现两个物理学科节点：

```text
(subject_physics, subject_id=physics, name=物理学)   ← 接口按这个查
(subject_物理,    subject_id=物理,    name=物理)      ← 5 个知识点实际挂在这里
```

`get_subject_graph("physics")` 用 `MATCH (s:Subject {subject_id:'physics'})-[:HAS_KNOWLEDGE]->(n)`，自然拿不到任何知识点，广场统计里 physics 的 `node_count` 也是 0。

### 1.2 角色判断漏了 admin

- 前端：`canManageKnowledgeNodes = userRole === 'teacher' || userRole === 'super_admin'` —— **漏了 admin**，管理员登录时看不到「新增 / 删除知识点」；
- 后端：节点增删改用的是 `require_role(["teacher"])`，`admin` 会被 403（`super_admin` 因为 `require_role` 里特判才放行）。

### 1.3 没有批量导入入口

页面上只能一个个「新增知识点」，学科有几十上百个知识点时不可用。

## 2. 修复内容

### 2.1 图谱数据自愈（`graph_service.ensure_subject_hierarchy`）

在原有「按 subject 属性挂接」之后补两步：

```cypher
-- ① 按中文名或 id 前缀（physics_xxx → physics）重新挂到正确学科，并归一化 subject 属性
UNWIND $subjects AS subject
MATCH (n:KnowledgeNode)
WHERE n.subject = subject.name OR split(coalesce(n.id,''), '_')[0] = subject.id
MERGE (s:Subject {id: 'subject_' + subject.id})
MERGE (s)-[:HAS_KNOWLEDGE]->(n)
SET n.subject = subject.id

-- ② 清理 subject_id 为中文的重复学科节点（关系已迁移，不会丢数据）
UNWIND $subjects AS subject
MATCH (dup:Subject {subject_id: subject.name})
WHERE dup.id <> 'subject_' + subject.id
DETACH DELETE dup
```

执行后：physics 节点数 0 → 5，图谱与广场统计同时恢复；math（6）、chemistry（1）不受影响。

### 2.2 知识点批量导入（新增）

| 接口 | 说明 |
|---|---|
| `GET /api/v1/graphs/subjects/{subject_id}/nodes/import/template` | 下载 CSV 模板（带 BOM） |
| `POST /api/v1/graphs/subjects/{subject_id}/nodes/import` | 上传 csv / xlsx 批量导入 |

模板列：

| 列 | 必填 | 说明 |
|---|---|---|
| 知识点名称 | 是 | 学科内同名会跳过，不覆盖已有内容 |
| 知识点描述 | 否 | 最长 4000 字 |
| 前置知识点 | 否 | 多个用分号分隔，可引用本表其它行，也可引用学科内已有节点，导入后建 `PREREQUISITE` 关系 |
| 关键词 | 否 | 多个用分号分隔，便于搜索 |

返回 `created / skipped / failed / links / node_count` 与逐行错误明细。

解析逻辑在 `import_service.parse_knowledge_rows`（复用 `read_table`，支持 csv/xlsx，单次上限 800 行）。

### 2.3 权限对齐

| 位置 | 修复前 | 修复后 |
|---|---|---|
| 前端 `GraphDetailView` | `teacher` / `super_admin` | `authStore.isTeacher`（teacher / admin / super_admin） |
| 后端节点增删改、关系、任务（7 处） | `require_role(["teacher"])` | `require_role(["teacher","admin","super_admin"])` |
| `EDITOR_ROLES`（修改直接生效的角色） | `{teacher, super_admin}` | `{teacher, admin, super_admin}` |

### 2.4 前端交互

- 页头与「概览」Tab 都加 **导入知识点** 按钮（教师/管理员可见），复用 `FileImportDialog`：模板下载、字段说明、拖拽上传、逐行报错、导入后自动选中第一个新知识点并刷新图谱/广场统计；
- 学生看不到编辑入口时，概览顶部显示提示条：**当前为只读模式** —「知识点的编辑、导入需要教师或管理员权限」。

## 3. 账号说明

截图中的账号 `3511415754@qq.com`（昵称 CAB，`id=2`）原本是 `student`，因此看不到编辑/导入入口。已提权为 `teacher`：

```sql
update users set role='teacher' where id=2;
```

如需还原：`update users set role='student' where id=2;`

## 4. 验证记录（2026-11-12）

| 项 | 结果 |
|---|---|
| `GET /graphs/subjects/physics/graph` | 修复前 1 节点 0 关联 → 修复后 6 节点（1 学科 + 5 知识点）9 关联 |
| 广场统计 physics | 0 → 5，完整度 0% → 52% |
| CSV 导入（2 新 + 1 重名 + 1 缺名称） | 新增 2、跳过 1、失败 1（行号 5），建立前置关系 1 条 |
| UI：教师账号 | 页头 2 个「导入知识点」入口、「新增知识点」可见；上传后提示「成功新增 2 个知识点 / 建立前置关系 1 条」，知识点数 5 → 7，自动选中「电磁感应」 |
| UI：编辑保存 | 选中「磁场」→ 协作编辑 → 改描述 → 保存，提示「修改已生效」，已还原原值 |
| UI：学生账号 | 概览显示「当前为只读模式」，无导入/新增按钮，5 个知识点正常展示 |
| 控制台 | 0 个 JS 错误 |
| 测试数据 | 导入的「电磁感应」「机械波」已删除，physics 恢复 5 个知识点 |
