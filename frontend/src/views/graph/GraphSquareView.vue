<template>
  <div class="graph-square">
    <div class="graph-square__header">
      <h2>知识图谱广场</h2>
      <div class="graph-square__actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索学科..."
          prefix-icon="Search"
          clearable
          class="graph-square__search"
          @input="handleSearch"
        />
        <el-select v-model="sortBy" placeholder="排序方式" style="width: 140px" @change="handleSort">
          <el-option label="默认" value="default" />
          <el-option label="节点数" value="node_count" />
          <el-option label="完整度" value="completeness" />
          <el-option label="名称" value="name" />
        </el-select>
        <el-tooltip content="仅显示有误解标注的学科" placement="top">
          <el-switch
            v-model="misconceptionOnly"
            active-text="仅有误解"
            inline-prompt
          />
        </el-tooltip>
        <el-button type="primary" @click="goToCrossSubject">
          <el-icon><Connection /></el-icon>
          跨学科关联图谱
        </el-button>
      </div>
    </div>

    <div v-loading="graphStore.loading" class="graph-square__grid">
      <el-row :gutter="16">
        <el-col
          v-for="subject in filteredStats"
          :key="subject.id"
          :xs="12"
          :sm="8"
          :md="6"
          :lg="4"
        >
          <el-tooltip
            :content="subjectTooltip(subject)"
            placement="top"
            :show-after="300"
          >
            <el-card
              shadow="hover"
              class="graph-square__card"
              @click="goToDetail(subject.id)"
              @mouseenter="loadSubjectPreview(subject.id)"
            >
              <div class="graph-square__card-icon" :style="{ background: subject.color + '20', color: subject.color }">
                <el-icon :size="32"><component :is="subject.icon" /></el-icon>
              </div>
              <h3 class="graph-square__card-name">{{ subject.name }}</h3>
              <div class="graph-square__card-stats">
                <span>{{ subject.node_count }} 个知识点</span>
              </div>
              <!-- Misconception 标注行 -->
              <div
                v-if="subject.misconception_count > 0"
                class="graph-square__card-misconception"
                @click.stop="goToDetailWithMcFilter(subject.id)"
              >
                <el-icon :size="14"><Warning /></el-icon>
                <span>{{ subject.misconception_count }} 个易误解知识点</span>
              </div>
              <div class="graph-square__card-progress">
                <span class="graph-square__card-progress-label">完整度</span>
                <el-progress
                  type="circle"
                  :width="48"
                  :percentage="subject.completeness"
                  :stroke-width="4"
                  :color="subject.color"
                />
              </div>
            </el-card>
          </el-tooltip>
        </el-col>
      </el-row>

      <el-empty v-if="filteredStats.length === 0 && !graphStore.loading" description="暂无学科数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 知识图谱广场视图
 * 12学科分类卡片网格 + 搜索 + 排序 + misconception标注 + 跨学科入口
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Warning, Connection } from '@element-plus/icons-vue'
import { useGraphStore } from '@/stores/graph'
import { graphApi } from '@/services/graph'
import type { SquareStat, KnowledgeNode } from '@/services/graph'

const router = useRouter()
const graphStore = useGraphStore()

const searchQuery = ref('')
const sortBy = ref('default')
const misconceptionOnly = ref(false)

/** 学科知识点预览缓存 */
const subjectNodePreview = ref<Record<string, KnowledgeNode[]>>({})

const filteredStats = computed(() => {
  let list = [...graphStore.squareStats]

  // 搜索过滤
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter((s) => s.name.toLowerCase().includes(q) || s.id.toLowerCase().includes(q))
  }

  // 仅有误解标注筛选
  if (misconceptionOnly.value) {
    list = list.filter((s) => s.misconception_count > 0)
  }

  // 排序
  switch (sortBy.value) {
    case 'node_count':
      list.sort((a, b) => b.node_count - a.node_count)
      break
    case 'completeness':
      list.sort((a, b) => b.completeness - a.completeness)
      break
    case 'name':
      list.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
      break
  }

  return list
})

function handleSearch(): void {
  // 搜索由 computed 自动处理
}

function handleSort(): void {
  // 排序由 computed 自动处理
}

function goToDetail(subjectId: string): void {
  router.push({
    name: 'GraphDetail',
    params: { id: subjectId },
  })
}

function goToDetailWithMcFilter(subjectId: string): void {
  router.push({
    name: 'GraphDetail',
    params: { id: subjectId },
    query: { mc_filter: '1' },
  })
}

function goToCrossSubject(): void {
  router.push({ name: 'CrossSubjectGraph' })
}

/** 生成学科卡片的 tooltip 内容 */
function subjectTooltip(subject: SquareStat): string {
  const preview = subjectNodePreview.value[subject.id]
  let tip = `${subject.name}：${subject.node_count} 个知识点，完整度 ${subject.completeness}%`
  if (subject.misconception_count > 0) {
    tip += `\n⚠ ${subject.misconception_count} 个易误解知识点`
  }
  if (preview && preview.length > 0) {
    tip += '\n\n知识点预览：'
    preview.slice(0, 5).forEach((n, i) => {
      tip += `\n${i + 1}. ${n.name || n.id}`
    })
  }
  return tip
}

/** 异步加载学科知识点预览 */
async function loadSubjectPreview(subjectId: string): Promise<void> {
  if (subjectNodePreview.value[subjectId]) return
  try {
    const nodes = await graphApi.searchNodes('', subjectId, 5)
    subjectNodePreview.value[subjectId] = nodes
  } catch {
    // 静默失败
  }
}

onMounted(async () => {
  await graphStore.loadSquareStats()
})
</script>

<style lang="scss" scoped>
.graph-square {
  &__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-lg);

    h2 {
      font-size: 22px;
      font-weight: 700;
      color: var(--color-text-primary);
    }
  }

  &__actions {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  &__search {
    width: 200px;
  }

  &__grid {
    min-height: 300px;
  }

  &__card {
    cursor: pointer;
    text-align: center;
    margin-bottom: var(--spacing-md);
    transition: transform 0.15s ease;

    &:hover {
      transform: translateY(-4px);
    }

    :deep(.el-card__body) {
      padding: 20px;
    }
  }

  &__card-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: 64px;
    border-radius: 50%;
    margin-bottom: 12px;
  }

  &__card-name {
    font-size: 16px;
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 6px;
  }

  &__card-stats {
    font-size: 13px;
    color: var(--color-text-secondary);
    margin-bottom: 8px;
  }

  &__card-misconception {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    font-size: 12px;
    color: #e6a23c;
    background: #fdf6ec;
    border-radius: 4px;
    padding: 4px 8px;
    margin-bottom: 8px;
    cursor: pointer;

    &:hover {
      background: #faecd8;
    }
  }

  &__card-progress {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }

  &__card-progress-label {
    font-size: 12px;
    color: var(--color-text-secondary);
  }
}
</style>
