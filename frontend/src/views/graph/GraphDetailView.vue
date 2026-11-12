<template>
  <div class="graph-detail">
    <div class="graph-detail__header">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回广场
      </el-button>
      <h2>{{ currentSubject?.name || id }}</h2>
      <div class="graph-detail__header-actions">
        <span v-if="graphStore.currentGraph" class="graph-detail__selected-node">
          当前知识点：{{ graphStore.currentGraph.name }}
        </span>
        <el-button v-if="canManageKnowledgeNodes" type="success" plain @click="knowledgeImportVisible = true">
          <el-icon><Upload /></el-icon>
          导入知识点
        </el-button>
        <el-button type="primary" :disabled="!graphStore.currentGraph" @click="openEditor('overview')">
          <el-icon><Edit /></el-icon>
          协作编辑
        </el-button>
        <el-button
          v-if="canManageKnowledgeNodes"
          type="danger"
          plain
          :disabled="!graphStore.currentGraph"
          @click="deleteSelectedNode"
        >
          <el-icon><Delete /></el-icon>
          删除知识点
        </el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab1: 概览 -->
      <el-tab-pane label="概览" name="overview">
        <el-alert
          v-if="!canManageKnowledgeNodes"
          class="graph-detail__readonly"
          type="info"
          :closable="false"
          show-icon
          title="当前为只读模式"
          description="知识点的编辑、导入需要教师或管理员权限；如需维护本学科图谱，请联系管理员开通。"
        />
        <div class="graph-detail__tab-actions">
          <el-button v-if="canManageKnowledgeNodes" type="success" @click="newNodeVisible = true">
            <el-icon><Plus /></el-icon> 新增知识点
          </el-button>
          <el-button
            v-if="canManageKnowledgeNodes"
            type="success"
            plain
            @click="knowledgeImportVisible = true"
          >
            <el-icon><Upload /></el-icon> 导入知识点
          </el-button>
          <el-button type="primary" :disabled="!selectedNodeId" @click="openEditor('overview')">
            <el-icon><Edit /></el-icon> 编辑概览
          </el-button>
          <el-button
            v-if="canManageKnowledgeNodes"
            type="danger"
            plain
            :disabled="!selectedNodeId"
            @click="deleteSelectedNode"
          >
            <el-icon><Delete /></el-icon> 删除知识点
          </el-button>
        </div>
        <el-descriptions :column="2" border v-loading="graphStore.loading">
          <el-descriptions-item label="学科">{{ currentSubject?.name }}</el-descriptions-item>
          <el-descriptions-item label="知识点数量">{{ currentSubject?.node_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="完整度">{{ currentSubject?.completeness || 0 }}%</el-descriptions-item>
          <el-descriptions-item label="易误解知识点">{{ currentSubject?.misconception_count || 0 }} 个</el-descriptions-item>
        </el-descriptions>

        <!-- 搜索节点 -->
        <div class="graph-detail__search-section">
          <h3>搜索知识点</h3>
          <el-input
            v-model="nodeQuery"
            placeholder="输入知识点名称..."
            @keyup.enter="searchNodes"
          >
            <template #append>
              <el-button @click="searchNodes">搜索</el-button>
            </template>
          </el-input>
          <div v-if="graphStore.searchResults.length > 0" class="graph-detail__search-results">
            <NodeCard
              v-for="node in graphStore.searchResults"
              :key="node.id"
              :node="node"
              :selected="selectedNodeId === node.id"
              @click="selectNode(node)"
              @open-misconception="openMisconceptionDialog(node)"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab2: 关联资源 -->
      <el-tab-pane label="关联资源" name="resources">
        <div class="graph-detail__tab-actions">
          <el-button type="primary" :disabled="!selectedNodeId" @click="openEditor('resources')">
            上传或编辑资源
          </el-button>
        </div>
        <el-table :data="nodeResources" empty-text="暂无关联资源" stripe>
          <el-table-column prop="title" label="资源名称" />
          <el-table-column prop="resource_type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.resource_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="file_size" label="大小" width="100">
            <template #default="{ row }">
              {{ row.file_size ? formatSize(row.file_size) : '-' }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Tab3: 关联关系 -->
      <el-tab-pane label="关联关系" name="relations">
        <div class="graph-detail__tab-actions">
          <el-button type="primary" :disabled="!selectedNodeId" @click="openEditor('relations')">
            构建或编辑关系
          </el-button>
        </div>
        <el-alert
          title="学科与知识点的关系图显示在页面下方；点击知识点可切换当前编辑对象。"
          type="info"
          :closable="false"
          show-icon
        />
        <div v-if="selectedLink" class="graph-detail__link-info">
          <LinkInfo :link="selectedLink" />
        </div>
      </el-tab-pane>

      <!-- Tab4: 认知目标 -->
      <el-tab-pane label="认知目标" name="cognitive">
        <div v-if="selectedNodeId" class="graph-detail__cognitive">
          <div class="graph-detail__section-header">
            <h3>{{ graphStore.currentGraph?.name || selectedNodeId }} 的认知目标</h3>
            <el-button type="primary" @click="openEditor('cognitive')">编辑认知目标</el-button>
          </div>
          <div ref="radarRef" class="graph-detail__radar"></div>
        </div>
        <el-empty v-else description="请先选择一个知识点" />
      </el-tab-pane>

      <!-- Tab5: 推荐 -->
      <el-tab-pane label="推荐" name="recommend">
        <div class="graph-detail__tab-actions">
          <el-button type="primary" :disabled="!selectedNodeId" @click="openEditor('recommendation')">
            编辑推荐
          </el-button>
        </div>
        <div v-if="recommendations.length > 0" class="graph-detail__recommendations">
          <el-card
            v-for="rec in recommendations"
            :key="rec.id"
            shadow="hover"
            class="graph-detail__rec-card"
            @click="selectNode(rec)"
          >
            <div class="graph-detail__rec-name">{{ rec.name || rec.id }}</div>
            <p v-if="rec.description" class="graph-detail__rec-desc">{{ rec.description }}</p>
            <div class="graph-detail__rec-tags">
              <el-tag v-if="rec.subject" size="small" type="info">{{ subjectNameMap[rec.subject] || rec.subject }}</el-tag>
              <el-tag
                v-if="(rec as any)._recommendation_reason === '跨学科关联节点'"
                size="small"
                type="warning"
                effect="dark"
              >
                跨学科
              </el-tag>
              <el-tag
                v-if="(rec as any)._recommendation_reason"
                size="small"
                type="success"
                effect="plain"
              >
                {{ (rec as any)._recommendation_reason }}
              </el-tag>
            </div>
          </el-card>
        </div>
        <el-empty v-else description="请先选择一个知识点获取推荐" />
      </el-tab-pane>

      <!-- Tab6: 任务 -->
      <el-tab-pane label="任务" name="tasks">
        <div v-if="selectedNodeId">
          <div v-if="isTeacher" class="graph-detail__tab-actions">
            <el-button type="primary" @click="openEditor('task')">布置任务</el-button>
          </div>
          <el-table
            v-if="graphStore.nodeTasks.length > 0"
            :data="graphStore.nodeTasks"
            empty-text="暂无关联任务"
            stripe
          >
            <el-table-column prop="name" label="任务名称" />
            <el-table-column prop="type" label="类型" width="120">
              <template #default="{ row }">
                <el-tag :type="taskTypeTagType(row.type)" size="small">
                  {{ taskTypeLabel(row.type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="taskStatusTagType(row.status)" size="small">
                  {{ taskStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="100">
              <template #default="{ row }">
                <el-tag size="small" type="info" effect="plain">{{ taskSourceLabel(row.source) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="due_date" label="截止时间" width="180">
              <template #default="{ row }">
                {{ row.due_date ? formatDate(row.due_date) : '-' }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无关联任务" />
        </div>
        <el-empty v-else description="请先选择一个知识点" />
      </el-tab-pane>
    </el-tabs>

    <el-card shadow="never" class="graph-detail__structure-card graph-detail__structure-card--bottom">
      <div class="graph-detail__structure-header">
        <div>
          <h3>学科知识结构图</h3>
          <p>中心节点代表学科，周围节点代表该学科包含的知识点。</p>
        </div>
        <el-tag type="info" effect="plain">学科 → 包含知识点</el-tag>
      </div>
      <ForceGraph
        :nodes="graphStore.subjectGraph.nodes"
        :links="graphStore.subjectGraph.links"
        :selected-node-id="selectedNodeId"
        height="460px"
        @node-click="handleGraphNodeClick"
        @node-hover="handleNodeHover"
        @link-click="handleLinkClick"
      />
    </el-card>

    <!-- 知识点导入 -->
    <FileImportDialog
      v-model="knowledgeImportVisible"
      title="导入知识点"
      :steps="KNOWLEDGE_IMPORT_STEPS"
      :field-rows="KNOWLEDGE_IMPORT_FIELDS"
      accept=".csv,.xlsx"
      accept-text="csv / xlsx"
      tip="支持 .csv / .xlsx，单文件不超过 5MB；同名知识点会跳过，不会覆盖已有内容"
      template-name="知识点导入模板.csv"
      :download-template="downloadKnowledgeTemplate"
      :submit="doImportKnowledge"
      @imported="onKnowledgeImported"
    />

    <!-- Misconception 详情弹窗 -->
    <MisconceptionDialog
      v-if="mcDialogVisible"
      :misconceptions="graphStore.misconceptions"
      :editable="isTeacher"
      @add="handleAddMc"
      @update="handleUpdateMc"
      @delete="handleDeleteMc"
      @suggest="handleSuggestMc"
      @close="mcDialogVisible = false"
    />

    <GraphEditDrawer
      v-if="graphStore.currentGraph"
      v-model="editorVisible"
      :node="graphStore.currentGraph"
      :initial-tab="editorInitialTab"
      :direct-apply="canManageKnowledgeNodes"
      :can-review="canManageKnowledgeNodes"
      :can-assign-task="canManageKnowledgeNodes"
      @changed="handleEditorChanged"
    />

    <el-dialog v-model="newNodeVisible" title="新增知识点" width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="所属学科">
          <el-input :model-value="currentSubject?.name || id" disabled />
        </el-form-item>
        <el-form-item label="知识点名称" required>
          <el-input v-model="newNodeForm.name" maxlength="200" placeholder="请输入知识点名称" />
        </el-form-item>
        <el-form-item label="知识点概览">
          <el-input
            v-model="newNodeForm.description"
            type="textarea"
            :rows="5"
            maxlength="2000"
            show-word-limit
            placeholder="请输入知识点说明"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newNodeVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingNode" @click="createKnowledgeNode">新增知识点</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4EDU 知识图谱详情视图
 * 六维Tab：概览/关联资源/关联关系/认知目标/推荐/任务
 * 支持 misconception 标注管理、真实任务数据、认知目标均值对比
 */
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Delete, Edit, Plus, Upload } from '@element-plus/icons-vue'
import FileImportDialog from '@/components/common/FileImportDialog.vue'
import type { ImportDialogResult, ImportFieldRow, ImportSummaryPart } from '@/components/common/importTypes'
import { useGraphStore } from '@/stores/graph'
import { useAuthStore } from '@/stores/auth'
import { graphApi, type KnowledgeImportResult } from '@/services/graph'
import ForceGraph from '@/components/graph/ForceGraph.vue'
import NodeCard from '@/components/graph/NodeCard.vue'
import LinkInfo from '@/components/graph/LinkInfo.vue'
import MisconceptionDialog from '@/components/graph/MisconceptionDialog.vue'
import GraphEditDrawer from '@/components/graph/GraphEditDrawer.vue'
import type { KnowledgeNode, GraphNode, GraphLink, MisconceptionInput } from '@/services/graph'

const route = useRoute()
const router = useRouter()
const graphStore = useGraphStore()
const authStore = useAuthStore()

const id = computed(() => route.params.id as string)
const activeTab = ref('overview')
const nodeQuery = ref('')
const selectedNodeId = ref<string | null>(null)
const nodeResources = ref<unknown[]>([])
const recommendations = ref<KnowledgeNode[]>([])
const selectedLink = ref<GraphLink | null>(null)
const radarRef = ref<HTMLDivElement | null>(null)
const mcDialogVisible = ref<boolean>(false)
const editorVisible = ref<boolean>(false)
const editorInitialTab = ref<string>('overview')
const newNodeVisible = ref<boolean>(false)
const creatingNode = ref<boolean>(false)
const newNodeForm = reactive({ name: '', description: '' })

/** 知识点批量导入 */
const knowledgeImportVisible = ref(false)

const KNOWLEDGE_IMPORT_STEPS = [
  '下载模板，至少填写「知识点名称」一列；描述、前置知识点、关键词都可留空',
  '前置知识点用分号分隔，可写本表里的其它知识点，也可写学科内已有知识点',
  '上传 .csv / .xlsx，系统逐行校验，同名知识点会被跳过（不会覆盖已有内容）',
]

const KNOWLEDGE_IMPORT_FIELDS: ImportFieldRow[] = [
  { field: '知识点名称', required: '是', desc: '如「牛顿第二定律」，与学科内已有知识点同名会跳过' },
  { field: '知识点描述', required: '否', desc: '一句话说明这个知识点讲什么，最长 4000 字' },
  { field: '前置知识点', required: '否', desc: '多个用分号分隔，如「牛顿第一定律;力的概念」；导入后自动建前置关系' },
  { field: '关键词', required: '否', desc: '多个用分号分隔，便于搜索，如「惯性;力」' },
]

const canManageKnowledgeNodes = computed(() =>
  // 原实现只判断 teacher / super_admin，漏了 admin，导致管理员账号也看不到编辑入口
  authStore.isTeacher
)
const isTeacher = canManageKnowledgeNodes

const subjectNameMap: Record<string, string> = {
  math: '数学', physics: '物理学', chemistry: '化学', biology: '生物学',
  cs: '计算机科学', chinese: '语文', english: '英语', history: '历史',
  geography: '地理', politics: '政治', pe: '体育', art: '艺术',
}

const currentSubject = computed(() =>
  graphStore.squareStats.find((s) => s.id === id.value)
)

function goBack(): void {
  router.push({ name: 'GraphSquare' })
}

function openEditor(tab: string): void {
  if (!graphStore.currentGraph) return
  editorInitialTab.value = tab
  editorVisible.value = true
}

async function createKnowledgeNode(): Promise<void> {
  if (!newNodeForm.name.trim()) {
    ElMessage.warning('请输入知识点名称')
    return
  }

  creatingNode.value = true
  try {
    const node = await graphApi.createNode({
      name: newNodeForm.name.trim(),
      subject: id.value,
      description: newNodeForm.description.trim() || undefined,
    })
    await Promise.all([
      graphStore.loadSquareStats(),
      graphStore.loadSubjectGraph(id.value),
      graphStore.searchNodes('', id.value),
    ])
    newNodeForm.name = ''
    newNodeForm.description = ''
    newNodeVisible.value = false
    await selectNode(node)
    ElMessage.success('知识点已新增')
  } finally {
    creatingNode.value = false
  }
}

async function doImportKnowledge(file: File): Promise<ImportDialogResult> {
  const res: KnowledgeImportResult = await graphApi.importKnowledgeNodes(id.value, file)
  const summary: ImportSummaryPart[] = [
    { text: `文件共 ${res.total} 行`, tone: 'muted' },
    { text: `新增 ${res.created} 个知识点`, tone: res.created ? 'ok' : 'bad' },
  ]
  if (res.skipped) summary.push({ text: `同名跳过 ${res.skipped} 个`, tone: 'warn' })
  if (res.failed) summary.push({ text: `未通过校验 ${res.failed} 行`, tone: 'bad' })
  if (res.links) summary.push({ text: `建立前置关系 ${res.links} 条`, tone: 'ok' })

  let title: string
  let tone: ImportDialogResult['tone']
  if (!res.created && !res.skipped) {
    title = '没有导入任何知识点，请按下方原因修正后重试'
    tone = 'error'
  } else if (res.failed) {
    title = `新增 ${res.created} 个知识点，${res.failed} 行未通过校验`
    tone = 'warning'
  } else if (!res.created && res.skipped) {
    title = `没有新增知识点：${res.skipped} 个已存在`
    tone = 'warning'
  } else {
    title = `成功新增 ${res.created} 个知识点`
    tone = 'success'
  }

  return { title, tone, summary, errors: res.errors, errorsTruncated: res.errors_truncated, payload: res }
}

async function downloadKnowledgeTemplate(): Promise<void> {
  await graphApi.downloadKnowledgeTemplate(id.value)
}

async function onKnowledgeImported(result: ImportDialogResult): Promise<void> {
  const payload = result.payload as KnowledgeImportResult | undefined
  if (!payload?.created) return
  await Promise.all([
    graphStore.loadSubjectGraph(id.value),
    graphStore.loadSquareStats(),
    graphStore.searchNodes('', id.value),
  ])
  const first = payload.created_rows?.[0]?.name
  const hit = graphStore.subjectGraph.nodes.find((n) => n.name === first)
  if (hit) await selectNode(hit as GraphNode)
}

async function deleteSelectedNode(): Promise<void> {
  const node = graphStore.currentGraph
  if (!node) return

  try {
    await ElMessageBox.confirm(
      `确定删除知识点“${node.name}”吗？相关关系、待审核修改和图谱任务也会被删除。`,
      '删除知识点',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch (action) {
    if (action === 'cancel' || action === 'close') return
    console.error('打开删除确认框失败:', action)
    return
  }

  try {
    await graphApi.deleteNode(node.id)
    clearNodeSelection()
    await Promise.all([
      graphStore.loadSquareStats(),
      graphStore.loadSubjectGraph(id.value),
      graphStore.searchNodes('', id.value),
    ])
    ElMessage.success('知识点已删除')
  } catch (error) {
    console.error('删除知识点失败:', error)
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return dateStr
  }
}

function taskTypeLabel(type: string): string {
  const labels: Record<string, string> = { learning: '学习', review: '复习', diagnosis: '诊断' }
  return labels[type] || type
}

function taskTypeTagType(type: string): 'success' | 'warning' | 'danger' {
  const map: Record<string, 'success' | 'warning' | 'danger'> = {
    learning: 'success', review: 'warning', diagnosis: 'danger',
  }
  return map[type] || 'warning'
}

function taskStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: '待开始', in_progress: '进行中', completed: '已完成',
  }
  return labels[status] || status
}

function taskStatusTagType(status: string): 'info' | 'primary' | 'success' {
  const map: Record<string, 'info' | 'primary' | 'success'> = {
    pending: 'info', in_progress: 'primary', completed: 'success',
  }
  return map[status] || 'info'
}

function taskSourceLabel(source: string): string {
  const labels: Record<string, string> = { course: '课程', diagnosis: '诊断' }
  return labels[source] || source
}

async function searchNodes(): Promise<void> {
  if (!nodeQuery.value.trim()) return
  await graphStore.searchNodes(nodeQuery.value, id.value)
}

async function selectNode(node: GraphNode): Promise<void> {
  if (selectedNodeId.value === node.id) {
    clearNodeSelection()
    return
  }
  selectedNodeId.value = node.id
  await graphStore.loadNodeDetail(node.id)
  await graphStore.loadNeighbors(node.id, 1, 50)
  await loadNodeResources(node.id)
  await loadRecommendations(node.id)
  await renderCognitiveRadar(node.id)
  // 加载该节点的任务
  await graphStore.loadNodeTasks(node.id)
  // 加载该节点的误解标注
  await graphStore.loadMisconceptions(node.id)
}

function clearNodeSelection(): void {
  editorVisible.value = false
  selectedNodeId.value = null
  graphStore.currentGraph = null
  nodeResources.value = []
  recommendations.value = []
  selectedLink.value = null
}

async function handleGraphNodeClick(node: GraphNode): Promise<void> {
  if (node.node_type === 'subject') return
  await selectNode(node)
}

async function handleEditorChanged(): Promise<void> {
  if (!selectedNodeId.value) return
  const nodeId = selectedNodeId.value
  await Promise.all([
    graphStore.loadNodeDetail(nodeId),
    graphStore.loadNeighbors(nodeId, 1, 50),
    graphStore.loadSubjectGraph(id.value),
    loadNodeResources(nodeId),
    loadRecommendations(nodeId),
    graphStore.loadNodeTasks(nodeId),
    graphStore.loadSquareStats(),
  ])
  await nextTick()
  await renderCognitiveRadar(nodeId)
}

async function loadNodeResources(nodeId: string): Promise<void> {
  try {
    nodeResources.value = await graphApi.getNodeResources(nodeId)
  } catch {
    nodeResources.value = []
  }
}

async function loadRecommendations(nodeId: string): Promise<void> {
  try {
    recommendations.value = await graphApi.getRecommendations(nodeId)
  } catch {
    recommendations.value = []
  }
}

function handleNodeHover(node: GraphNode | null): void {
  if (!node) {
    selectedLink.value = null
  }
}

function handleLinkClick(link: GraphLink): void {
  selectedLink.value = link
}

// ========== Misconception 管理 ==========

function openMisconceptionDialog(node: KnowledgeNode): void {
  selectedNodeId.value = node.id
  graphStore.loadMisconceptions(node.id).then(() => {
    mcDialogVisible.value = true
  })
}

async function handleAddMc(data: MisconceptionInput): Promise<void> {
  if (!selectedNodeId.value) return
  try {
    await graphStore.addMisconception(selectedNodeId.value, data)
  } catch {
    // 错误已在 store 中处理
  }
}

async function handleUpdateMc(mcId: string, data: Partial<MisconceptionInput>): Promise<void> {
  if (!selectedNodeId.value) return
  try {
    await graphStore.updateMisconception(selectedNodeId.value, mcId, data)
  } catch {
    // 错误已在 store 中处理
  }
}

async function handleDeleteMc(mcId: string): Promise<void> {
  if (!selectedNodeId.value) return
  try {
    await graphStore.deleteMisconception(selectedNodeId.value, mcId)
    if (graphStore.misconceptions.length === 0) {
      mcDialogVisible.value = false
    }
  } catch {
    // 错误已在 store 中处理
  }
}

async function handleSuggestMc(): Promise<void> {
  if (!selectedNodeId.value) return
  const suggestions = await graphStore.suggestMisconceptions(selectedNodeId.value)
  if (suggestions.length === 0) {
    // 无建议时提示
    return
  }
  // 逐条确认添加
  for (const sug of suggestions) {
    try {
      await graphStore.addMisconception(selectedNodeId.value, {
        misconception: sug.misconception,
        correction: sug.correction,
        topic: sug.topic,
        keywords: sug.keywords,
      })
    } catch {
      // 跳过失败项
    }
  }
}

// ========== 认知目标雷达图 ==========

async function renderCognitiveRadar(nodeId: string): Promise<void> {
  try {
    // P1: 携带 include_avg=true 获取学科均值
    await graphStore.loadCognitiveGoal(nodeId, true)
    const data = graphStore.cognitiveGoal
    if (!data || !radarRef.value) return

    const echarts = await import('echarts')
    const chart = echarts.init(radarRef.value)

    const seriesData: Array<{ value: number[]; name: string; areaStyle?: { opacity: number } }> = [
      {
        value: data.values,
        name: data.node_name,
        areaStyle: { opacity: 0.3 },
      },
    ]

    // P1: 学科均值对比线
    if (data.subject_avg && data.subject_avg.length > 0) {
      seriesData.push({
        value: data.subject_avg,
        name: '学科均值',
        areaStyle: { opacity: 0.1 },
      })
    }

    chart.setOption({
      title: { text: data.node_name + ' 认知目标', left: 'center' },
      tooltip: {},
      legend: {
        data: seriesData.map((s) => s.name),
        bottom: 10,
      },
      radar: {
        indicator: data.dimensions.map((d) => ({ name: d, max: 100 })),
        shape: 'circle',
        splitNumber: 5,
      },
      series: [
        {
          type: 'radar',
          data: seriesData,
        },
      ],
    })

    const resizeObserver = new ResizeObserver(() => chart.resize())
    resizeObserver.observe(radarRef.value)
  } catch (error) {
    console.error('渲染认知目标雷达图失败:', error)
  }
}

// 监听 Tab 切换
watch(activeTab, async (tab) => {
  if (tab === 'relations' && !selectedNodeId.value) {
    await graphStore.searchNodes('', id.value)
    if (graphStore.searchResults.length > 0) {
      await selectNode(graphStore.searchResults[0])
    }
  }
})

onMounted(async () => {
  if (!graphStore.squareStats.length) {
    await graphStore.loadSquareStats()
  }
  await Promise.all([
    graphStore.searchNodes('', id.value),
    graphStore.loadSubjectGraph(id.value),
  ])
})
</script>

<style lang="scss" scoped>
.graph-detail {
  &__header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: var(--spacing-lg);

    h2 {
      font-size: 20px;
      font-weight: 700;
      color: var(--color-text-primary);
    }
  }

  &__header-actions {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  &__selected-node {
    color: var(--color-text-secondary);
    font-size: 13px;
  }

  &__structure-card {
    margin-bottom: var(--spacing-lg);

    :deep(.el-card__body) {
      padding: 20px;
    }

    &--bottom {
      margin-top: var(--spacing-lg);
      margin-bottom: 0;
    }
  }

  &__structure-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 16px;

    h3 {
      margin: 0 0 6px;
      font-size: 18px;
    }

    p {
      margin: 0;
      color: var(--color-text-secondary);
      font-size: 13px;
    }
  }

  &__tab-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-bottom: 24px;
  }

  &__readonly {
    margin-bottom: 16px;
  }

  &__section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;

    h3 {
      margin-bottom: 0;
    }
  }

  &__search-section {
    margin-top: var(--spacing-lg);

    h3 {
      margin-bottom: 10px;
      font-size: 16px;
    }
  }

  &__search-results {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 12px;
    margin-top: 12px;
  }

  &__link-info {
    margin-top: 16px;
  }

  &__cognitive {
    h3 {
      margin-bottom: 16px;
    }
  }

  &__radar {
    width: 100%;
    height: 400px;
  }

  &__recommendations {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 12px;
  }

  &__rec-card {
    cursor: pointer;
    transition: transform 0.15s ease;

    &:hover {
      transform: translateY(-2px);
    }
  }

  &__rec-name {
    font-weight: 600;
    margin-bottom: 4px;
  }

  &__rec-desc {
    font-size: 13px;
    color: var(--color-text-secondary);
    margin-bottom: 8px;
  }

  &__rec-tags {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
}
</style>
