<template>
  <el-dialog
    v-model="visible"
    title="⚠ 常见误解标注"
    width="600px"
    @close="handleClose"
  >
    <!-- 空状态 -->
    <el-empty v-if="misconceptions.length === 0" description="暂无误解标注">
      <el-button v-if="editable" type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon> 添加误解标注
      </el-button>
      <el-button v-if="editable" @click="handleSuggest">
        <el-icon><MagicStick /></el-icon> AI 辅助标注
      </el-button>
    </el-empty>

    <!-- 误解详情列表（分页） -->
    <template v-else>
      <div class="misconception-dialog__content">
        <!-- 当前页误解 -->
        <div class="misconception-dialog__item">
          <!-- 误解描述 -->
          <div class="misconception-dialog__section misconception-dialog__section--error">
            <div class="misconception-dialog__section-label">❌ 误解</div>
            <div class="misconception-dialog__section-text">
              {{ currentMc.misconception }}
            </div>
          </div>

          <!-- 纠正说明 -->
          <div class="misconception-dialog__section misconception-dialog__section--correct">
            <div class="misconception-dialog__section-label">✅ 纠正</div>
            <div class="misconception-dialog__section-text">
              {{ currentMc.correction }}
            </div>
          </div>

          <!-- 主题 -->
          <div class="misconception-dialog__meta">
            <span class="misconception-dialog__meta-item">
              📌 主题：{{ currentMc.topic }}
            </span>
            <span class="misconception-dialog__meta-item misconception-dialog__meta-item--source">
              🏷 来源：{{ sourceLabel(currentMc.source) }}
              <template v-if="currentMc.annotated_at">
                · {{ formatDate(currentMc.annotated_at) }}
              </template>
            </span>
          </div>

          <!-- 关键词 -->
          <div v-if="currentMc.keywords && currentMc.keywords.length > 0" class="misconception-dialog__keywords">
            <el-tag
              v-for="kw in currentMc.keywords"
              :key="kw"
              size="small"
              type="warning"
              effect="plain"
            >
              {{ kw }}
            </el-tag>
          </div>

          <!-- 置信度 -->
          <div v-if="currentMc.source === 'ai'" class="misconception-dialog__confidence">
            置信度：{{ Math.round(currentMc.confidence * 100) }}%
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="misconceptions.length > 1" class="misconception-dialog__pagination">
          <el-button size="small" :disabled="currentIndex === 0" @click="prevPage">
            上一条
          </el-button>
          <span class="misconception-dialog__pagination-info">
            {{ currentIndex + 1 }} / {{ misconceptions.length }}
          </span>
          <el-button
            size="small"
            :disabled="currentIndex === misconceptions.length - 1"
            @click="nextPage"
          >
            下一条
          </el-button>
        </div>
      </div>
    </template>

    <!-- 底部操作 -->
    <template #footer>
      <div class="misconception-dialog__footer">
        <div class="misconception-dialog__footer-left">
          <el-button v-if="editable" @click="handleSuggest">
            <el-icon><MagicStick /></el-icon> AI 辅助标注
          </el-button>
        </div>
        <div class="misconception-dialog__footer-right">
          <el-button v-if="editable && misconceptions.length > 0" @click="handleEdit">
            编辑
          </el-button>
          <el-button
            v-if="editable && misconceptions.length > 0"
            type="danger"
            plain
            @click="handleDelete"
          >
            删除
          </el-button>
          <el-button v-if="editable" type="primary" @click="handleAdd">
            添加
          </el-button>
          <el-button @click="handleClose">关闭</el-button>
        </div>
      </div>
    </template>

    <!-- 添加/编辑表单弹窗 -->
    <el-dialog
      v-model="formVisible"
      :title="editingMc ? '编辑误解标注' : '添加误解标注'"
      width="500px"
      append-to-body
    >
      <el-form :model="formData" label-width="80px" label-position="top">
        <el-form-item label="误解描述" required>
          <el-input
            v-model="formData.misconception"
            type="textarea"
            :rows="2"
            placeholder="描述常见的错误概念..."
          />
        </el-form-item>
        <el-form-item label="纠正说明" required>
          <el-input
            v-model="formData.correction"
            type="textarea"
            :rows="4"
            placeholder="描述正确的理解..."
          />
        </el-form-item>
        <el-form-item label="主题" required>
          <el-input v-model="formData.topic" placeholder="如：牛顿运动定律" />
        </el-form-item>
        <el-form-item label="关键词">
          <div class="misconception-dialog__keyword-input">
            <el-input
              v-model="newKeyword"
              size="small"
              placeholder="输入关键词后回车"
              style="width: 200px"
              @keyup.enter="addKeyword"
            />
            <el-button size="small" @click="addKeyword">添加</el-button>
          </div>
          <div class="misconception-dialog__keyword-tags">
            <el-tag
              v-for="(kw, idx) in formData.keywords"
              :key="idx"
              closable
              size="small"
              @close="removeKeyword(idx)"
            >
              {{ kw }}
            </el-tag>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 Misconception 详情弹窗组件
 * 显示误解（❌红色）、纠正（✅绿色）、主题、来源标记
 * 支持分页翻页、教师模式编辑/删除/AI辅助标注
 */
import { ref, computed, watch } from 'vue'
import { Plus, MagicStick } from '@element-plus/icons-vue'
import type { Misconception, MisconceptionInput } from '@/services/graph'

const props = withDefaults(defineProps<{
  misconceptions: Misconception[]
  editable?: boolean
}>(), {
  editable: false,
})

const emit = defineEmits<{
  (e: 'add', data: MisconceptionInput): void
  (e: 'update', mcId: string, data: Partial<MisconceptionInput>): void
  (e: 'delete', mcId: string): void
  (e: 'suggest'): void
  (e: 'close'): void
}>()

const visible = ref<boolean>(true)
const currentIndex = ref<number>(0)
const formVisible = ref<boolean>(false)
const editingMc = ref<Misconception | null>(null)
const newKeyword = ref<string>('')

const formData = ref<MisconceptionInput>({
  misconception: '',
  correction: '',
  topic: '',
  keywords: [],
})

const currentMc = computed<Misconception>(() => {
  if (props.misconceptions.length === 0) {
    return {
      mc_id: '',
      misconception: '',
      correction: '',
      topic: '',
      keywords: [],
      source: 'system',
      annotated_by: null,
      annotated_at: '',
      confidence: 0,
    }
  }
  return props.misconceptions[currentIndex.value] || props.misconceptions[0]
})

// 当 misconceptions 列表变化时，重置索引
watch(
  () => props.misconceptions,
  () => {
    if (currentIndex.value >= props.misconceptions.length) {
      currentIndex.value = Math.max(0, props.misconceptions.length - 1)
    }
  },
)

function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    teacher: '教师标注',
    ai: 'AI辅助标注',
    system: '系统预置',
  }
  return labels[source] || source
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  } catch {
    return dateStr
  }
}

function prevPage(): void {
  if (currentIndex.value > 0) {
    currentIndex.value--
  }
}

function nextPage(): void {
  if (currentIndex.value < props.misconceptions.length - 1) {
    currentIndex.value++
  }
}

function handleAdd(): void {
  editingMc.value = null
  formData.value = { misconception: '', correction: '', topic: '', keywords: [] }
  formVisible.value = true
}

function handleEdit(): void {
  editingMc.value = currentMc.value
  formData.value = {
    misconception: currentMc.value.misconception,
    correction: currentMc.value.correction,
    topic: currentMc.value.topic,
    keywords: [...currentMc.value.keywords],
  }
  formVisible.value = true
}

function handleDelete(): void {
  emit('delete', currentMc.value.mc_id)
}

function handleSuggest(): void {
  emit('suggest')
}

function handleClose(): void {
  visible.value = false
  emit('close')
}

function addKeyword(): void {
  const kw = newKeyword.value.trim()
  if (kw && !formData.value.keywords.includes(kw)) {
    formData.value.keywords.push(kw)
  }
  newKeyword.value = ''
}

function removeKeyword(idx: number): void {
  formData.value.keywords.splice(idx, 1)
}

function submitForm(): void {
  if (!formData.value.misconception || !formData.value.correction || !formData.value.topic) {
    return
  }
  if (editingMc.value) {
    emit('update', editingMc.value.mc_id, { ...formData.value })
  } else {
    emit('add', { ...formData.value })
  }
  formVisible.value = false
}
</script>

<style lang="scss" scoped>
.misconception-dialog {
  &__content {
    min-height: 200px;
  }

  &__item {
    padding: 4px 0;
  }

  &__section {
    margin-bottom: 16px;

    &--error {
      .misconception-dialog__section-label {
        color: #f56c6c;
      }
      .misconception-dialog__section-text {
        color: #f56c6c;
      }
    }

    &--correct {
      .misconception-dialog__section-label {
        color: #67c23a;
      }
      .misconception-dialog__section-text {
        color: #67c23a;
      }
    }
  }

  &__section-label {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 6px;
  }

  &__section-text {
    font-size: 14px;
    line-height: 1.6;
    padding-left: 8px;
  }

  &__meta {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 12px;
    padding: 8px 12px;
    background: #f5f7fa;
    border-radius: 4px;
  }

  &__meta-item {
    font-size: 13px;
    color: #606266;

    &--source {
      color: #909399;
      font-size: 12px;
    }
  }

  &__keywords {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 8px;
  }

  &__confidence {
    font-size: 12px;
    color: #909399;
  }

  &__pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding-top: 12px;
    border-top: 1px solid #ebeef5;
  }

  &__pagination-info {
    font-size: 14px;
    color: #606266;
  }

  &__footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  &__footer-right {
    display: flex;
    gap: 8px;
  }

  &__keyword-input {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
  }

  &__keyword-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
}
</style>
