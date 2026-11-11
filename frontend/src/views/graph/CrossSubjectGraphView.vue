<template>
  <div class="cross-graph">
    <div class="cross-graph__header">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon> 返回广场
      </el-button>
      <h2>跨学科关联图谱</h2>
    </div>

    <!-- 学科选择器 + 配置 -->
    <el-card shadow="never" class="cross-graph__config">
      <div class="cross-graph__config-row">
        <div class="cross-graph__config-item">
          <label class="cross-graph__config-label">选择学科（至少2个）</label>
          <el-select
            v-model="selectedSubjects"
            multiple
            :max-collapse-tags="4"
            placeholder="选择2个或以上学科"
            style="width: 400px"
          >
            <el-option
              v-for="s in allSubjects"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            />
          </el-select>
        </div>

        <div class="cross-graph__config-item">
          <label class="cross-graph__config-label">关系强度阈值: {{ minStrength.toFixed(1) }}</label>
          <el-slider
            v-model="minStrength"
            :min="0"
            :max="1"
            :step="0.1"
            style="width: 200px"
          />
        </div>

        <div class="cross-graph__config-item">
          <label class="cross-graph__config-label">最大节点数</label>
          <el-input-number
            v-model="maxNodes"
            :min="10"
            :max="500"
            :step="10"
          />
        </div>

        <el-button
          type="primary"
          :disabled="selectedSubjects.length < 2"
          :loading="graphStore.loading"
          @click="buildGraph"
        >
          <el-icon><Connection /></el-icon>
          构建图谱
        </el-button>
      </div>
    </el-card>

    <!-- 图谱可视化区域 -->
    <div v-if="graphStore.crossSubjectData" class="cross-graph__main">
      <el-row :gutter="16">
        <el-col :span="18">
          <el-card shadow="never" class="cross-graph__graph-card">
            <ForceGraph
              :nodes="crossNodes"
              :links="crossLinks"
              :cross-subject-mode="true"
              :subject-colors="subjectColors"
              height="600px"
              @node-click="onNodeClick"
              @link-click="onLinkClick"
            />
          </el-card>
        </el-col>
        <el-col :span="6">
          <!-- 统计面板 -->
          <el-card shadow="never" class="cross-graph__stats">
            <template #header><span>统计面板</span></template>
            <div class="cross-graph__stats-list">
              <div class="cross-graph__stat-item">
                <span class="cross-graph__stat-label">总节点数</span>
                <span class="cross-graph__stat-value">{{ stats.total_nodes }}</span>
              </div>
              <div class="cross-graph__stat-item">
                <span class="cross-graph__stat-label">总关系数</span>
                <span class="cross-graph__stat-value">{{ stats.total_links }}</span>
              </div>
              <div class="cross-graph__stat-item">
                <span class="cross-graph__stat-label">跨学科关系</span>
                <span class="cross-graph__stat-value cross-graph__stat-value--highlight">{{ stats.cross_links }}</span>
              </div>
              <div class="cross-graph__stat-item">
                <span class="cross-graph__stat-label">平均强度</span>
                <span class="cross-graph__stat-value">{{ stats.avg_strength.toFixed(2) }}</span>
              </div>
            </div>

            <!-- 学科分布 -->
            <el-divider content-position="left">学科分布</el-divider>
            <div class="cross-graph__distribution">
              <div
                v-for="(count, subj) in stats.subject_distribution"
                :key="subj"
                class="cross-graph__dist-item"
              >
                <span class="cross-graph__dist-dot" :style="{ background: subjectColors[subj] || '#999' }" />
                <span class="cross-graph__dist-name">{{ subjectNameMap[subj] || subj }}</span>
                <span class="cross-graph__dist-count">{{ count }}</span>
              </div>
            </div>

            <!-- Top 5 最强跨学科关系 -->
            <el-divider v-if="topCrossPairs.length > 0" content-position="left">最强跨学科关联 Top 5</el-divider>
            <div v-if="topCrossPairs.length > 0" class="cross-graph__top-pairs">
              <div
                v-for="(pair, idx) in topCrossPairs"
                :key="idx"
                class="cross-graph__pair-item"
              >
                <span class="cross-graph__pair-rank">{{ idx + 1 }}</span>
                <span class="cross-graph__pair-link">{{ pair.source }} → {{ pair.target }}</span>
                <el-tag size="small" :type="strengthTagType(pair.strength)" effect="dark">
                  {{ pair.strength_label }} {{ pair.strength.toFixed(2) }}
                </el-tag>
              </div>
            </div>
          </el-card>

          <!-- 图例 -->
          <CrossSubjectLegend
            :subjects="selectedSubjects"
            :subject-colors="subjectColors"
            :subject-name-map="subjectNameMap"
          />
        </el-col>
      </el-row>
    </div>

    <!-- 空状态 -->
    <el-empty
      v-else
      description='请选择至少2个学科并点击"构建图谱"按钮'
      :image-size="120"
    />

    <!-- 关系详情弹窗 -->
    <el-dialog v-model="linkDialogVisible" title="关系详情" width="500px">
      <LinkInfo v-if="selectedLink" :link="selectedLink" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4EDU 跨学科关联图谱视图
 * 支持学科选择、强度筛选、力导向图可视化、统计面板、图例
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Connection } from '@element-plus/icons-vue'
import { useGraphStore } from '@/stores/graph'
import ForceGraph from '@/components/graph/ForceGraph.vue'
import LinkInfo from '@/components/graph/LinkInfo.vue'
import CrossSubjectLegend from '@/components/graph/CrossSubjectLegend.vue'
import type { CrossSubjectNode, CrossSubjectLink, CrossSubjectStats, GraphNode, GraphLink } from '@/services/graph'

const router = useRouter()
const graphStore = useGraphStore()

const selectedSubjects = ref<string[]>(['math', 'physics'])
const minStrength = ref(0.0)
const maxNodes = ref(100)
const linkDialogVisible = ref(false)
const selectedLink = ref<GraphLink | null>(null)

// 学科列表
const allSubjects = [
  { id: 'math', name: '数学' },
  { id: 'physics', name: '物理学' },
  { id: 'chemistry', name: '化学' },
  { id: 'biology', name: '生物学' },
  { id: 'cs', name: '计算机科学' },
  { id: 'chinese', name: '语文' },
  { id: 'english', name: '英语' },
  { id: 'history', name: '历史' },
  { id: 'geography', name: '地理' },
  { id: 'politics', name: '政治' },
  { id: 'pe', name: '体育' },
  { id: 'art', name: '艺术' },
]

const subjectColors: Record<string, string> = {
  math: '#1976D2', physics: '#F57C00', chemistry: '#4CAF50', biology: '#388E3C',
  cs: '#7B1FA2', chinese: '#D32F2F', english: '#00796B', history: '#5D4037',
  geography: '#0288D1', politics: '#C62828', pe: '#FF6F00', art: '#AD1457',
}

const subjectNameMap: Record<string, string> = {
  math: '数学', physics: '物理学', chemistry: '化学', biology: '生物学',
  cs: '计算机科学', chinese: '语文', english: '英语', history: '历史',
  geography: '地理', politics: '政治', pe: '体育', art: '艺术',
}

// 图谱数据
const crossNodes = computed<CrossSubjectNode[]>(() => {
  return graphStore.crossSubjectData?.nodes || []
})

const crossLinks = computed<CrossSubjectLink[]>(() => {
  return graphStore.crossSubjectData?.links || []
})

const stats = computed<CrossSubjectStats>(() => {
  return graphStore.crossSubjectData?.stats || {
    total_nodes: 0,
    total_links: 0,
    cross_links: 0,
    avg_strength: 0,
    subject_distribution: {},
    top_cross_pairs: [],
  }
})

const topCrossPairs = computed(() => stats.value.top_cross_pairs || [])

function strengthTagType(strength: number): 'success' | 'warning' | 'danger' {
  if (strength >= 0.7) return 'success'
  if (strength >= 0.4) return 'warning'
  return 'danger'
}

function goBack(): void {
  router.push({ name: 'GraphSquare' })
}

async function buildGraph(): Promise<void> {
  if (selectedSubjects.value.length < 2) return
  await graphStore.loadCrossSubject(selectedSubjects.value, minStrength.value, maxNodes.value)
}

function onNodeClick(node: GraphNode): void {
  if (node.node_type === 'subject') {
    router.push({
      name: 'GraphDetail',
      params: { id: node.subject_id || node.subject },
    })
    return
  }
  router.push({
    name: 'GraphDetail',
    params: { id: node.subject },
    query: { node: node.id },
  })
}

function onLinkClick(link: GraphLink): void {
  selectedLink.value = {
    source: link.source,
    target: link.target,
    type: link.type,
    label: link.label,
    strength: link.strength,
    strength_label: link.strength_label,
    is_cross: link.is_cross,
  }
  linkDialogVisible.value = true
}

onMounted(() => {
  void buildGraph()
})
</script>

<style lang="scss" scoped>
.cross-graph {
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

  &__config {
    margin-bottom: var(--spacing-md);

    :deep(.el-card__body) {
      padding: 16px 20px;
    }
  }

  &__config-row {
    display: flex;
    align-items: flex-end;
    gap: 24px;
    flex-wrap: wrap;
  }

  &__config-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  &__config-label {
    font-size: 13px;
    color: var(--color-text-secondary);
  }

  &__main {
    margin-top: var(--spacing-md);
  }

  &__graph-card {
    :deep(.el-card__body) {
      padding: 0;
    }
  }

  &__stats {
    margin-bottom: var(--spacing-md);
  }

  &__stats-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  &__stat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 0;
  }

  &__stat-label {
    font-size: 14px;
    color: var(--color-text-secondary);
  }

  &__stat-value {
    font-size: 20px;
    font-weight: 700;
    color: var(--color-text-primary);

    &--highlight {
      color: #e6a23c;
    }
  }

  &__distribution {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__dist-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  &__dist-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  &__dist-name {
    flex: 1;
    color: var(--color-text-primary);
  }

  &__dist-count {
    font-weight: 600;
    color: var(--color-text-secondary);
  }

  &__top-pairs {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__pair-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
  }

  &__pair-rank {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e6a23c;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
  }

  &__pair-link {
    flex: 1;
    color: var(--color-text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
