<template>
  <el-dialog
    :model-value="visible"
    :title="evaluation ? '编辑评价' : '写评价'"
    width="560px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="90px" label-position="right">
      <el-form-item label="评价类型" prop="evaluation_type">
        <el-select v-model="formData.evaluation_type" placeholder="请选择评价类型" style="width: 100%">
          <el-option label="综合评价" value="overall" />
          <el-option label="学业表现" value="academic" />
          <el-option label="学习态度" value="attitude" />
          <el-option label="进步评价" value="improvement" />
        </el-select>
      </el-form-item>

      <el-form-item label="评分" prop="rating">
        <el-rate
          v-model="formData.rating"
          :max="5"
          show-score
          :texts="['很差', '较差', '一般', '良好', '优秀']"
        />
      </el-form-item>

      <el-form-item label="评价内容" prop="content">
        <el-input
          v-model="formData.content"
          type="textarea"
          :rows="4"
          placeholder="请输入评价内容..."
          maxlength="500"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="学习建议" prop="suggestion">
        <el-input
          v-model="formData.suggestion"
          type="textarea"
          :rows="3"
          placeholder="请输入学习建议（可选）..."
          maxlength="300"
          show-word-limit
        />
      </el-form-item>

      <el-form-item label="学生可见">
        <el-switch v-model="formData.is_visible" />
        <span class="form-tip">{{ formData.is_visible ? '学生可以查看此评价' : '学生无法查看此评价' }}</span>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ evaluation ? '保存' : '发布评价' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 评价表单组件
 * 支持创建新评价和编辑已有评价
 */
import { ref, reactive, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useGrowthStore } from '@/stores/growth'
import type { EvaluationItem } from '@/services/growth'

const props = defineProps<{
  visible: boolean
  evaluation?: EvaluationItem | null
  studentId: number
  courseId?: number
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
  success: [evaluation: EvaluationItem]
}>()

const growthStore = useGrowthStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const formData = reactive({
  evaluation_type: 'overall',
  rating: 5,
  content: '',
  suggestion: '',
  is_visible: true,
})

const rules: FormRules = {
  evaluation_type: [{ required: true, message: '请选择评价类型', trigger: 'change' }],
  rating: [{ required: true, message: '请选择评分', trigger: 'change' }],
  content: [
    { required: true, message: '请输入评价内容', trigger: 'blur' },
    { min: 5, message: '评价内容至少5个字符', trigger: 'blur' },
  ],
}

/** 监听对话框打开，初始化表单数据 */
watch(
  () => props.visible,
  (val) => {
    if (val) {
      if (props.evaluation) {
        formData.evaluation_type = props.evaluation.evaluation_type
        formData.rating = props.evaluation.rating
        formData.content = props.evaluation.content
        formData.suggestion = props.evaluation.suggestion || ''
        formData.is_visible = props.evaluation.is_visible
      } else {
        formData.evaluation_type = 'overall'
        formData.rating = 5
        formData.content = ''
        formData.suggestion = ''
        formData.is_visible = true
      }
    }
  },
)

async function handleSubmit(): Promise<void> {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (props.evaluation) {
        // 编辑模式
        const result = await growthStore.updateEvaluation(props.evaluation.id, {
          evaluation_type: formData.evaluation_type,
          rating: formData.rating,
          content: formData.content,
          suggestion: formData.suggestion || undefined,
          is_visible: formData.is_visible,
        })
        if (result) {
          emit('success', result)
          emit('update:visible', false)
        }
      } else {
        // 创建模式
        const result = await growthStore.createEvaluation({
          student_id: props.studentId,
          course_id: props.courseId,
          evaluation_type: formData.evaluation_type,
          rating: formData.rating,
          content: formData.content,
          suggestion: formData.suggestion || undefined,
          is_visible: formData.is_visible,
        })
        if (result) {
          emit('success', result)
          emit('update:visible', false)
        }
      }
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style lang="scss" scoped>
.form-tip {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}
</style>
