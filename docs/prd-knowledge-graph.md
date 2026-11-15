# 智慧学伴 知识图谱模块 PRD

> **文档版本**: v1.0  
> **撰写人**: 许清楚（Xu，产品经理）  
> **日期**: 2025-07-13  
> **分支**: YeGen_Module_3.4_图谱

---

## 1. 项目信息

| 项目 | 说明 |
|------|------|
| **项目名称** | ai4edu_knowledge_graph |
| **前端技术栈** | Vue 3 + TypeScript + Element Plus + Pinia + ECharts + D3 |
| **后端技术栈** | FastAPI + SQLAlchemy 2.0 (async) + Neo4j 5 + PostgreSQL |
| **开发分支** | `YeGen_Module_3.4_图谱` |
| **增量基线** | 项目已有图谱基础代码（GraphSquareView / GraphDetailView / ForceGraph / graph_service.py 等），本 PRD 在此基础上做增量需求规划 |

### 原始需求复述

在已有图谱基础代码上，开发三个子功能模块：

1. **图谱广场（权限：全体用户）** — 优化12学科分类展示和完整度评分体系，新增 Anti-Misconception 标注功能
2. **图谱详情 - 六维 Tab（权限：学生+教师）** — 优化概览/关联资源/关联关系/认知目标/推荐/任务六个 Tab，任务 Tab 从 mock 数据改为真实数据
3. **跨学科关联图谱（权限：学生，全新功能）** — 多学科知识点网络构建，展示跨学科隐含关联和关系强度

---

## 2. 产品目标

| 编号 | 目标 | 衡量指标 |
|------|------|----------|
| **G1** | 帮助学生快速识别和规避常见认知误区，降低因 misconception 导致的学习障碍 | Anti-Misconception 标注覆盖率 ≥ 80% 已知易错知识点；标注知识点点击查看纠正率达 ≥ 60% |
| **G2** | 打破学科壁垒，让学生发现跨学科知识关联，促进知识迁移与综合应用能力 | 跨学科图谱支持 ≥ 2 学科组合查询；跨学科关联路径平均展示 ≥ 3 条 |
| **G3** | 提升图谱详情页的信息完整度和实用性，让任务 Tab 从 mock 走向真实可用 | 任务 Tab 真实数据绑定率 100%；六维 Tab 页面加载时间 ≤ 2s |

### 核心问题与价值主张

- **问题 1**：学生在学习某些知识点时容易形成错误概念（如"重的物体下落快"），但现有平台未在图谱层面给出预警
- **问题 2**：学科之间有大量隐含关联（如微积分↔物理运动学），但现有图谱以单学科为边界，学生难以发现跨学科联系
- **问题 3**：详情页任务 Tab 使用硬编码 mock 数据，无法反映真实学习任务进度

**价值主张**：通过 Anti-Misconception 标注、跨学科关联图谱和真实任务数据，让知识图谱从"静态展示工具"升级为"认知预警 + 跨学科发现 + 学习追踪"的主动学习辅助系统。

---

## 3. 用户故事

### 全体用户

| 编号 | 用户故事 |
|------|----------|
| US-1 | 作为用户，我希望在图谱广场看到每个学科的完整度评分，以便快速了解哪些学科的知识图谱建设较为完善 |
| US-2 | 作为用户，我希望在图谱广场看到哪些知识点存在常见误解标注，以便在浏览时对这些知识点提高警惕 |
| US-3 | 作为用户，我希望能按"是否有误解标注"筛选学科卡片，以便快速定位需要关注的内容 |

### 学生

| 编号 | 用户故事 |
|------|----------|
| US-4 | 作为学生，我希望在图谱详情页查看某个知识点的完整信息（描述、关联资源、关系网络、认知目标、推荐、任务），以便全面了解该知识点 |
| US-5 | 作为学生，我希望在任务 Tab 看到与当前知识点相关的真实学习任务及完成状态，以便跟踪我的学习进度 |
| US-6 | 作为学生，我希望能选择 2 个或以上学科来构建跨学科知识点关联网络，以便发现不同学科间的隐含联系 |
| US-7 | 作为学生，我希望在跨学科图谱中看到学科间的关系强度可视化（如连线粗细/颜色深浅），以便判断关联的紧密程度 |
| US-8 | 作为学生，我希望点击 Anti-Misconception 标注的节点后能看到具体的误解描述和纠正说明，以便修正我的错误认知 |

### 教师

| 编号 | 用户故事 |
|------|----------|
| US-9 | 作为教师，我希望能为知识点手动添加或编辑 misconception 标注，以便针对我教学中的实际案例进行预警 |
| US-10 | 作为教师，我希望在详情页任务 Tab 看到我为某知识点布置的学习任务，以便管理教学进度 |
| US-11 | 作为教师，我希望能查看跨学科关联图谱，以便设计跨学科教学方案 |

---

## 4. 需求池

### P0 — Must Have

| 编号 | 需求描述 | 验收标准 | 权限角色 |
|------|----------|----------|----------|
| **KG-P0-01** | **完整度评分体系优化**：重构 `calculate_completeness` 方法，将评分维度从 2 维（属性填充 + 关系密度）扩展为 4 维加权：节点描述填充率（20%）、认知水平填充率（20%）、关系密度（30%）、资源覆盖率（30%） | ① 评分公式包含 4 个维度且权重可配置 ② 资源覆盖率 = 有 HAS_RESOURCE 关系的节点数 / 总节点数 ③ 评分范围 0-100，无节点时返回 0 ④ 学科广场卡片显示更新后的评分 | 全体用户 |
| **KG-P0-02** | **Anti-Misconception 节点标注 — 数据层**：在 Neo4j KnowledgeNode 节点上增加 `has_misconception` 布尔属性和 `misconceptions` JSON 属性，存储该知识点的误解数据 | ① Neo4j 节点支持 `has_misconception: boolean` 和 `misconceptions: list<json>` 属性 ② 提供按 `has_misconception=true` 过滤节点的查询能力 ③ `get_square_stats` 返回每个学科的 misconception 节点计数 | 全体用户 |
| **KG-P0-03** | **Anti-Misconception 节点标注 — 展示层**：在图谱广场学科卡片上展示 misconception 标注图标和计数；在详情页节点搜索结果中标注带误解的节点 | ① 学科卡片显示 warning 图标 + "N 个易误解知识点" ② NodeCard 组件对 `has_misconception=true` 的节点显示橙色 warning 角标 ③ hover/click 角标显示误解列表弹窗 ④ 误解弹窗包含：误解描述 + 纠正说明 + 来源标记 | 全体用户 |
| **KG-P0-04** | **Anti-Misconception 标注管理（教师）**：教师可对知识点添加/编辑/删除 misconception 标注 | ① 提供后端 API `POST /graphs/nodes/{node_id}/misconceptions` 创建标注 ② 提供 `PUT /graphs/nodes/{node_id}/misconceptions/{mc_id}` 编辑标注 ③ 提供 `DELETE /graphs/nodes/{node_id}/misconceptions/{mc_id}` 删除标注 ④ 标注记录标注者 ID 和时间 | 教师 |
| **KG-P0-05** | **任务 Tab 真实数据绑定**：将 GraphDetailView 的任务 Tab 从 mock 数据改为从后端获取真实任务数据 | ① 后端提供 `GET /graphs/nodes/{node_id}/tasks` API ② 任务数据来源：关联课程的作业任务 + 学习诊断中的知识点关联诊断 ③ 任务 Tab 展示任务名称、类型（学习/复习/诊断）、状态（待开始/进行中/已完成）、截止时间 ④ 无任务时显示空状态提示 | 学生、教师 |
| **KG-P0-06** | **跨学科关联图谱 — 后端查询**：提供跨学科知识点关联网络的查询 API | ① API `GET /graphs/cross-subject?subjects=math,physics` 接受 ≥2 个学科 ID ② 返回跨学科节点和关系，关系包含 `strength` 字段（0-1） ③ 关系强度算法：共同邻居数 + 共同资源 + 关系类型权重 ④ 返回数据包含同学科内部关系和跨学科关系，跨学科关系有 `is_cross: true` 标记 | 学生 |
| **KG-P0-07** | **跨学科关联图谱 — 前端可视化**：新增跨学科图谱视图，支持学科选择和网络可视化 | ① 提供 ≥2 学科的多选选择器 ② 选择后渲染力导向图，同学科节点按学科颜色着色 ③ 跨学科关系用虚线 + 渐变色连接，线条粗细映射关系强度 ④ 节点可拖拽、缩放、hover 显示详情 ⑤ 提供图例说明（颜色=学科、线型=关系类型、粗细=强度） | 学生 |

### P1 — Should Have

| 编号 | 需求描述 | 验收标准 | 权限角色 |
|------|----------|----------|----------|
| **KG-P1-01** | **学科卡片展示优化**：优化图谱广场学科卡片布局，增加 misconception 标注信息展示、hover 预览知识点列表 | ① 卡片显示节点数、完整度、misconception 计数 ② hover 卡片显示该学科前 5 个知识点的 tooltip ③ 卡片支持"仅有误解标注"筛选 toggle | 全体用户 |
| **KG-P1-02** | **Anti-Misconception AI 辅助标注**：基于已有 `AntiMisconceptionAgent` 的规则库，自动匹配知识点名称与 misconception topic，生成 AI 标注建议 | ① 后端提供 `POST /graphs/nodes/{node_id}/misconceptions/auto-suggest` API ② 匹配算法：节点 name 与 COMMON_MISCONCEPTIONS 中 topic 做关键词匹配 ③ 返回建议的 misconception 列表，教师确认后写入 ④ AI 标注的 misconception 记录 `source: "ai"` | 教师 |
| **KG-P1-03** | **跨学科关系强度可视化增强**：在跨学科图谱中提供关系强度筛选滑块和统计面板 | ① 提供强度筛选滑块（0-1），过滤显示低强度关系 ② 统计面板显示：总跨学科关系数、平均强度、最强关联 Top 5 ③ 点击关系线显示关系详情弹窗 | 学生 |
| **KG-P1-04** | **认知目标雷达图增强**：在认知目标 Tab 增加班级均值对比线 | ① 雷达图同时展示当前节点认知水平和同学科均值 ② 图例区分"当前知识点"和"学科均值" ③ 均值数据由后端聚合计算 | 学生、教师 |
| **KG-P1-05** | **推荐算法优化**：优化推荐 Tab 的推荐逻辑，增加跨学科推荐 | ① 推荐来源包括：同路径兄弟节点（50%）+ 同学科相似节点（30%）+ 跨学科关联节点（20%） ② 跨学科推荐标注"跨学科"标签 ③ 推荐结果附推荐理由 | 学生、教师 |

### P2 — Nice to Have

| 编号 | 需求描述 | 验收标准 | 权限角色 |
|------|----------|----------|----------|
| **KG-P2-01** | **图谱广场搜索增强**：支持跨学科关键词搜索，搜索结果直接跳转到对应知识点详情 | ① 搜索结果展示知识点名称、所属学科、misconception 标记 ② 点击结果跳转到该知识点的详情页 | 全体用户 |
| **KG-P2-02** | **跨学科关联图谱导出**：支持将跨学科图谱导出为 PNG 图片 | ① 提供导出按钮 ② 导出图片包含图例和标题 ③ 导出分辨率 ≥ 1920x1080 | 学生 |
| **KG-P2-03** | **Anti-Misconception 统计面板**：在图谱广场增加全局 misconception 统计概览 | ① 显示全平台 misconception 标注总数 ② 按学科分布的饼图 ③ 按来源（教师/AI）分布的统计 | 全体用户 |
| **KG-P2-04** | **ForceGraph 性能优化**：当节点数 > 100 时切换为 Canvas 渲染 | ① 节点数 ≤ 100 使用 SVG 渲染 ② 节点数 > 100 自动切换 Canvas 渲染 ③ 切换时无闪烁 | 全体用户 |

---

## 5. Anti-Misconception 功能详细设计

### 5.1 什么是 Anti-Misconception 标注

Anti-Misconception 标注是对知识图谱中**容易产生认知误区/错误概念**的知识点进行特殊标记的功能。其目的是：

- 在用户浏览图谱时**主动预警**该知识点存在常见误解
- 提供误解的**具体描述**和**正确纠正说明**
- 帮助学生在学习前建立正确认知框架，避免形成难以纠正的错误概念

> **现有基础**：项目已有 `AntiMisconceptionAgent`（`backend/app/agents/anti_misconception_agent.py`），包含 10 条常见 misconception 规则库（覆盖物理、化学、数学、生物、地理），支持基于关键词的检测和 LLM 纠正。本功能将该能力从**对话场景**延伸到**图谱可视化场景**。

### 5.2 数据结构设计

#### 5.2.1 Neo4j 节点属性扩展

在现有 `KnowledgeNode` 标签上增加两个属性：

```
KnowledgeNode {
  id: string                    // 已有
  name: string                  // 已有
  subject: string               // 已有
  description: string           // 已有
  cognitive_level: json         // 已有
  has_misconception: boolean    // 新增：是否存在误解标注
  misconceptions: json          // 新增：误解数据列表
}
```

#### 5.2.2 `misconceptions` JSON 结构

```json
[
  {
    "mc_id": "mc_001",
    "misconception": "重的物体比轻的物体下落快",
    "correction": "在真空中（忽略空气阻力），所有物体下落加速度相同，与质量无关。",
    "topic": "牛顿运动定律",
    "keywords": ["重的下落快", "质量大落得快"],
    "source": "teacher",          // "teacher" | "ai" | "system"
    "annotated_by": 123,          // 标注者用户ID (ai/system时为null)
    "annotated_at": "2025-07-13T10:00:00Z",
    "confidence": 1.0             // AI标注置信度 0-1，教师标注固定1.0
  }
]
```

#### 5.2.3 后端 API 设计

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/graphs/nodes/{node_id}/misconceptions` | 获取节点的误解标注列表 | 全体用户 |
| POST | `/graphs/nodes/{node_id}/misconceptions` | 添加误解标注 | 教师 |
| PUT | `/graphs/nodes/{node_id}/misconceptions/{mc_id}` | 编辑误解标注 | 教师 |
| DELETE | `/graphs/nodes/{node_id}/misconceptions/{mc_id}` | 删除误解标注 | 教师 |
| POST | `/graphs/nodes/{node_id}/misconceptions/auto-suggest` | AI辅助标注建议 | 教师 |
| GET | `/graphs/square` （扩展） | 广场统计增加 `misconception_count` 字段 | 全体用户 |

#### 5.2.4 前端 Service / Store 扩展

`services/graph.ts` 新增方法：

```typescript
// 获取节点误解标注
async getMisconceptions(nodeId: string): Promise<Misconception[]>

// 教师添加误解标注
async addMisconception(nodeId: string, data: MisconceptionInput): Promise<Misconception>

// 教师编辑误解标注
async updateMisconception(nodeId: string, mcId: string, data: Partial<MisconceptionInput>): Promise<Misconception>

// 教师删除误解标注
async deleteMisconception(nodeId: string, mcId: string): Promise<void>

// AI辅助标注建议
async suggestMisconceptions(nodeId: string): Promise<Misconception[]>
```

### 5.3 标注展示方式

#### 5.3.1 图谱广场 — 学科卡片

```
┌──────────────────────────┐
│      [学科图标]            │
│      物理学                │
│      15 个知识点            │
│                          │
│  ⚠ 3 个易误解知识点         │  ← 橙色 warning 行，仅在 misconception_count > 0 时显示
│                          │
│      [完整度 72%]          │
└──────────────────────────┘
```

- **图标**：Element Plus `Warning` 图标，橙色（`#E6A23C`）
- **文案**：`⚠ N 个易误解知识点`
- **条件**：`misconception_count > 0` 时显示
- **交互**：点击该行筛选显示带标注的知识点列表

#### 5.3.2 节点卡片（NodeCard）

```
┌──────────────────────────┐
│ ● 函数基础          ⚠    │  ← 右上角橙色角标
│ 函数的概念、定义域...       │
│ [数学]                    │
└──────────────────────────┘
```

- **角标**：右上角 `Warning` 图标，橙色背景圆形
- **条件**：`node.has_misconception === true`
- **交互**：hover 角标显示误解摘要 tooltip；click 角标打开误解详情弹窗

#### 5.3.3 误解详情弹窗

```
┌─────────────────────────────────────────┐
│ ⚠ 常见误解标注                    [×]    │
├─────────────────────────────────────────┤
│                                         │
│  ❌ 误解：重的物体比轻的物体下落快          │
│                                         │
│  ✅ 纠正：                                │
│  在真空中（忽略空气阻力），所有物体下落      │
│  加速度相同，与质量无关。伽利略的比萨斜塔     │
│  实验证明了这一点。                        │
│                                         │
│  📌 主题：牛顿运动定律                     │
│  🏷 来源：教师标注 · 2025-07-13           │
│                                         │
├─────────────────────────────────────────┤
│  [上一条]  1/3  [下一条]                  │
└─────────────────────────────────────────┘
```

- **颜色规范**：
  - 误解描述：红色文字（`#F56C6C`），前缀 ❌
  - 纠正说明：绿色文字（`#67C23A`），前缀 ✅
  - 来源标记：灰色小字（`#909399`）
- **分页**：当节点有多个 misconception 时支持翻页

#### 5.3.4 力导向图中的标注

- 带 misconception 的节点边框加粗为橙色（`stroke: #E6A23C; stroke-width: 3`）
- 节点旁显示小号 warning 图标

### 5.4 标注来源

| 来源 | 标识 | 说明 | 置信度 |
|------|------|------|--------|
| **教师手动标注** | `source: "teacher"` | 教师在详情页或管理界面手动添加 | 1.0（固定） |
| **AI 辅助标注** | `source: "ai"` | 基于 `AntiMisconceptionAgent` 规则库自动匹配，教师确认后写入 | 0.5-1.0（由匹配度决定） |
| **系统预置** | `source: "system"` | 从 `COMMON_MISCONCEPTIONS` 规则库初始化导入 | 1.0（固定） |

**AI 辅助标注流程**：

1. 教师在节点详情页点击"AI 辅助标注"按钮
2. 后端调用 `AntiMisconceptionAgent.detect_misconceptions(node.name + node.description)` 匹配规则库
3. 返回匹配到的 misconception 建议列表（含置信度）
4. 教师在弹窗中确认/编辑/拒绝每条建议
5. 确认的建议以 `source: "ai"` 写入节点 `misconceptions` 属性

---

## 6. 跨学科关联图谱详细设计

### 6.1 交互流程

```
用户进入跨学科图谱页面
        │
        ▼
┌─────────────────────────┐
│  Step 1: 选择学科        │
│  □ 数学  □ 物理学        │
│  □ 化学  □ 生物学        │
│  □ 计算机  □ ...         │
│  (至少选择 2 个学科)      │
└───────────┬─────────────┘
            │ 用户选择 ≥ 2 学科
            ▼
┌─────────────────────────┐
│  Step 2: 配置参数        │
│  关系强度阈值: ━━●━━ 0.3 │
│  最大节点数:   100       │
│  [构建图谱]              │
└───────────┬─────────────┘
            │ 点击"构建图谱"
            ▼
┌─────────────────────────┐
│  Step 3: 图谱展示        │
│  ┌───────────────────┐  │
│  │                   │  │
│  │  力导向图渲染      │  │
│  │  (同学科按颜色分区) │  │
│  │  (跨学科虚线连接)   │  │
│  │                   │  │
│  └───────────────────┘  │
│  [图例] [统计面板] [导出] │
└───────────┬─────────────┘
            │ 用户点击节点/关系
            ▼
┌─────────────────────────┐
│  Step 4: 详情交互        │
│  - 点击节点 → 跳转详情页  │
│  - 点击关系 → 显示关系详情 │
│  - 拖拽/缩放/重置         │
└─────────────────────────┘
```

### 6.2 数据模型设计

#### 6.2.1 后端 API

```
GET /graphs/cross-subject
  Query Parameters:
    - subjects: string (逗号分隔，如 "math,physics,chemistry")
    - min_strength: float (默认 0.0，范围 0-1)
    - max_nodes: int (默认 100，范围 10-500)
  Response:
    {
      "nodes": [
        {
          "id": "math_derivative",
          "name": "导数",
          "subject": "math",
          "description": "...",
          "has_misconception": false
        },
        ...
      ],
      "links": [
        {
          "source": "math_derivative",
          "target": "physics_newton_law",
          "type": "APPLICATION",
          "label": "运动学应用",
          "is_cross": true,        // 是否跨学科关系
          "strength": 0.85,         // 关系强度 0-1
          "strength_label": "强"    // 强/中/弱
        },
        {
          "source": "math_limit",
          "target": "math_derivative",
          "type": "PREREQUISITE",
          "label": "前置知识",
          "is_cross": false,
          "strength": 1.0,
          "strength_label": "强"
        }
      ],
      "stats": {
        "total_nodes": 42,
        "total_links": 58,
        "cross_links": 12,
        "avg_strength": 0.72,
        "subject_distribution": {"math": 20, "physics": 22}
      }
    }
```

#### 6.2.2 关系强度算法

```
strength = w1 * common_neighbors + w2 * common_resources + w3 * rel_type_weight

其中:
  - common_neighbors: 共同邻居节点数归一化 (0-1)，权重 w1 = 0.4
  - common_resources: 共同关联资源数归一化 (0-1)，权重 w2 = 0.3
  - rel_type_weight: 关系类型权重，权重 w3 = 0.3
    - PREREQUISITE: 1.0（前置关系，强关联）
    - APPLICATION: 0.8（应用关系，较强）
    - RELATED: 0.5（一般关联）
    - HAS_RESOURCE: 0.3（资源共享，弱关联）

strength_label:
  - strength >= 0.7 → "强"
  - 0.4 <= strength < 0.7 → "中"
  - strength < 0.4 → "弱"
```

#### 6.2.3 Cypher 查询设计

```cypher
// 获取选定学科的所有节点
MATCH (n:KnowledgeNode)
WHERE n.subject IN $subjects
RETURN n

// 获取选定学科内 + 跨学科的关系
MATCH (a:KnowledgeNode)-[r]->(b:KnowledgeNode)
WHERE a.subject IN $subjects AND b.subject IN $subjects
RETURN a.id AS source, b.id AS target,
       type(r) AS type, r.label AS label,
       a.subject AS source_subject, b.subject AS target_subject,
       CASE WHEN a.subject <> b.subject THEN true ELSE false END AS is_cross

// 计算共同邻居数（用于关系强度）
MATCH (a:KnowledgeNode {id: $node_a})-[:RELATED]-(common:KnowledgeNode)-[:RELATED]-(b:KnowledgeNode {id: $node_b})
RETURN count(DISTINCT common) AS common_count
```

#### 6.2.4 前端组件设计

新增视图组件：`views/graph/CrossSubjectGraphView.vue`

```
<template>
  <div class="cross-graph">
    <!-- 学科选择器 -->
    <div class="cross-graph__selector">
      <el-select v-model="selectedSubjects" multiple :max-collapse-tags="4" 
                 placeholder="选择2个或以上学科">
        <el-option v-for="s in allSubjects" :key="s.id" 
                   :label="s.name" :value="s.id" />
      </el-select>
      <el-slider v-model="minStrength" :min="0" :max="1" :step="0.1" />
      <el-button type="primary" :disabled="selectedSubjects.length < 2"
                 @click="buildGraph">构建图谱</el-button>
    </div>

    <!-- 图谱可视化 -->
    <ForceGraph
      :nodes="crossNodes" :links="crossLinks"
      :cross-subject-mode="true"
      height="600px"
      @node-click="onNodeClick" @link-click="onLinkClick"
    />

    <!-- 统计面板 -->
    <div class="cross-graph__stats">
      <el-statistic title="总节点数" :value="stats.total_nodes" />
      <el-statistic title="跨学科关系" :value="stats.cross_links" />
      <el-statistic title="平均强度" :value="stats.avg_strength" />
    </div>

    <!-- 图例 -->
    <div class="cross-graph__legend">
      <span>● 同学科节点</span>
      <span>- 同学科关系</span>
      <span>⋯ 跨学科关系（虚线）</span>
      <span>━━ 强关联</span>
      <span>── 中关联</span>
      <span>·· 弱关联</span>
    </div>
  </div>
</template>
```

### 6.3 可视化方案

#### 6.3.1 节点视觉规范

| 元素 | 同学科节点 | 跨学科枢纽节点 |
|------|-----------|---------------|
| 填充色 | 学科主题色 | 学科主题色 |
| 边框色 | `#FFFFFF` | `#FF9800`（橙色，表示跨学科枢纽） |
| 边框宽度 | 2px | 3px |
| 节点半径 | 16-32px（按度数） | 16-32px（按度数） |
| 标签 | 节点名称 | 节点名称 |

> **跨学科枢纽节点**：同时与 ≥2 个学科节点有关系的节点，用橙色边框高亮。

#### 6.3.2 关系视觉规范

| 关系类型 | 线型 | 颜色 | 粗细映射 |
|---------|------|------|----------|
| 同学科关系 | 实线 | `#CCCCCC` | `1 + strength * 3` px |
| 跨学科关系 | 虚线 | 渐变色（源节点色→目标节点色） | `1 + strength * 4` px |
| PREREQUISITE | 实线 + 箭头 | `#999999` | 固定 2px |
| APPLICATION | 虚线 + 箭头 | `#2196F3` | `1 + strength * 3` px |

#### 6.3.3 布局策略

- 使用现有 `ForceGraph.vue` 组件的力导向布局
- 增加**学科聚合力**：同学科节点之间增加额外引力，使同学科节点倾向于聚集
- 跨学科关系作为**桥梁连接**，自然将不同学科群落拉开

#### 6.3.4 路由设计

```typescript
// 新增路由
{
  path: 'graph/cross-subject',
  name: 'CrossSubjectGraph',
  component: () => import('@/views/graph/CrossSubjectGraphView.vue'),
  meta: {
    title: '跨学科关联图谱',
    requiresAuth: true,
    allowedRoles: ['student', 'teacher', 'admin'],
  },
}
```

---

## 7. 权限设计

### 7.1 权限矩阵

| 功能 | student | teacher | admin | super_admin | 未登录 |
|------|---------|---------|-------|-------------|--------|
| **图谱广场 — 浏览学科卡片** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **图谱广场 — 搜索/排序** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **图谱广场 — 查看 misconception 标注** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **图谱广场 — misconception 筛选** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **图谱详情 — 概览 Tab** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **图谱详情 — 关联资源 Tab** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **图谱详情 — 关联关系 Tab** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **图谱详情 — 认知目标 Tab** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **图谱详情 — 推荐 Tab** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **图谱详情 — 任务 Tab** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **节点 CRUD — 创建节点** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **节点 CRUD — 编辑节点** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **关系 CRUD — 创建/删除关系** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Anti-Misconception — 查看标注** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Anti-Misconception — 添加/编辑/删除标注** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **Anti-Misconception — AI 辅助标注** | ❌ | ✅ | ✅ | ✅ | ❌ |
| **跨学科关联图谱 — 查看** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **跨学科关联图谱 — 导出** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **跨学科关联图谱 — 构建查询** | ✅ | ✅ | ✅ | ✅ | ❌ |

> **说明**：根据原始需求，跨学科关联图谱权限为"学生"，但教师和管理员自然应具备更高权限，因此此处设定为 student+ 均可访问。所有图谱功能均需要登录（`requiresAuth: true`）。

### 7.2 后端权限实现

利用现有 `require_role` 依赖注入：

```python
from app.dependencies import get_current_user, require_role

# 全体用户可访问
@router.get("/square")
async def get_square(user: User = Depends(get_current_user)) -> APIResponse: ...

# 仅教师可操作
@router.post("/nodes/{node_id}/misconceptions")
async def add_misconception(
    node_id: str,
    user: User = Depends(require_role(["teacher", "admin", "super_admin"]))
) -> APIResponse: ...
```

### 7.3 前端路由守卫

```typescript
// scene-routes.ts 中新增 allowedRoles meta
{
  path: 'graph/cross-subject',
  name: 'CrossSubjectGraph',
  meta: {
    requiresAuth: true,
    allowedRoles: ['student', 'teacher', 'admin', 'super_admin'],
  },
}
```

---

## 8. 待确认问题

| 编号 | 问题 | 影响范围 | 建议方案 |
|------|------|----------|----------|
| **Q1** | **subject 字段值不一致**：种子数据中 `subject` 使用中文名（"数学"、"物理"），但 `SUBJECT_CATEGORIES` 和查询使用英文 ID（"math"、"physics"），导致按学科查询可能不匹配 | 全模块 | 统一使用英文 ID 作为 subject 值，中文名仅用于展示。需迁移已有种子数据 |
| **Q2** | **任务 Tab 数据来源**：当前系统无独立的"任务"模型。任务数据应来自哪里？是关联课程的作业任务、学习诊断、还是需要新建任务模型？ | KG-P0-05 | 建议优先关联 Diagnosis 模型（已有 `knowledge_points` JSON 字段）+ 课程作业。若短期无课程作业模型，先只关联 Diagnosis |
| **Q3** | **完整度评分权重是否可配置**：4 维权重（描述 20% / 认知 20% / 关系 30% / 资源 30%）是否需要支持后台动态配置，还是硬编码？ | KG-P0-01 | 建议 v1 硬编码，后续迭代加入配置表 |
| **Q4** | **AI 辅助标注的置信度阈值**：AI 匹配的 misconception 建议在什么置信度以下不展示给教师？ | KG-P1-02 | 建议阈值 0.5，低于此值不展示 |
| **Q5** | **跨学科图谱节点上限**：当选择的学科节点总数过多时（如 > 500），是否需要分页或抽样展示？ | KG-P0-07 | 建议默认上限 100，通过 `max_nodes` 参数控制，超限时提示用户缩小范围 |
| **Q6** | **misconception 数据初始化**：是否需要从 `COMMON_MISCONCEPTIONS` 规则库自动初始化已有知识节点的 misconception 标注？ | KG-P0-02 | 建议提供一次性初始化脚本，按 topic 与节点 name 匹配，以 `source: "system"` 写入 |
| **Q7** | **跨学科关联图谱入口位置**：跨学科图谱是从图谱广场进入（如广场顶部增加入口按钮），还是作为独立菜单项？ | KG-P0-07 | 建议在图谱广场页面增加"跨学科关联图谱"入口按钮，同时侧边栏增加菜单项 |
| **Q8** | **cognitive_level JSON key 不一致**：种子数据中 `cognitive_level` 使用中文 key（"记忆"、"理解"），但 `get_cognitive_goals` 方法使用英文 key（"remember"、"understand"），导致雷达图数据可能全为 0 | KG-P1-04 | 统一使用英文 key（remember/understand/apply/analyze/evaluate/create），需迁移种子数据 |

---

## 附录 A：现有代码盘点

### 前端

| 文件 | 功能 | 增量需求 |
|------|------|----------|
| `views/graph/GraphSquareView.vue` | 12 学科卡片网格 + 搜索 + 排序 | 增加 misconception 标注展示、跨学科入口 |
| `views/graph/GraphDetailView.vue` | 六维 Tab 详情页 | 任务 Tab 真实数据、misconception 标注展示 |
| `components/graph/ForceGraph.vue` | D3 力导向图（自定义简化版） | 支持跨学科模式（虚线、渐变、学科聚合力） |
| `components/graph/NodeCard.vue` | 节点卡片 | 增加 misconception 角标 |
| `components/graph/LinkInfo.vue` | 关系详情 | 增加关系强度展示 |
| `services/graph.ts` | API Service | 增加 misconception CRUD、跨学科查询、任务查询 |
| `stores/graph.ts` | Pinia Store | 增加 misconception、跨学科、任务状态管理 |

### 后端

| 文件 | 功能 | 增量需求 |
|------|------|----------|
| `api/v1/graphs.py` | 图谱 REST API | 增加 misconception CRUD、跨学科查询、任务查询端点 |
| `services/graph_service.py` | Neo4j 服务 | 完整度优化、misconception 管理、跨学科查询、任务查询 |
| `agents/anti_misconception_agent.py` | 反误解 Agent（规则库 + LLM） | 复用规则库做 AI 辅助标注建议 |
| `models/diagnosis.py` | 学习诊断模型 | 任务 Tab 数据来源之一 |
| `dependencies.py` | 认证与权限依赖 | 图谱 API 增加 `get_current_user` / `require_role` |

### Neo4j 数据模型

```
(KnowledgeNode)
  id: string
  name: string
  subject: string
  description: string
  cognitive_level: json
  has_misconception: boolean    ← 新增
  misconceptions: json          ← 新增

关系类型:
  - RELATED (已有)
  - PREREQUISITE (已有，种子数据)
  - APPLICATION (已有，种子数据)
  - HAS_RESOURCE (已有)
```

### 新增文件清单

| 文件路径 | 说明 |
|----------|------|
| `frontend/src/views/graph/CrossSubjectGraphView.vue` | 跨学科关联图谱视图 |
| `frontend/src/components/graph/MisconceptionBadge.vue` | Misconception 标注角标组件 |
| `frontend/src/components/graph/MisconceptionDialog.vue` | Misconception 详情弹窗组件 |
| `frontend/src/components/graph/CrossSubjectLegend.vue` | 跨学科图例组件 |
| `backend/app/api/v1/graphs.py`（扩展） | 新增 misconception、跨学科、任务 API 端点 |
| `backend/app/services/graph_service.py`（扩展） | 新增完整度优化、misconception、跨学科、任务方法 |
