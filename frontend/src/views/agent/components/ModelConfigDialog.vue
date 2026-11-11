<template>
  <el-dialog
    :model-value="modelValue"
    title="模型配置"
    width="760px"
    :close-on-click-modal="false"
    class="model-config"
    @update:model-value="close"
    @open="load"
  >
    <div v-loading="loading" class="model-config__body">
      <el-alert type="info" :closable="false" show-icon class="model-config__tip">
        <template #title>
          填写任一服务商的 API Key 即可启用 AI 对话。Key 以 AES 加密保存在服务端，页面只显示掩码；
          Key 输入框留空表示沿用已保存的值。
        </template>
      </el-alert>

      <el-collapse v-model="active">
        <el-collapse-item v-for="p in providers" :key="p.provider" :name="p.provider">
          <template #title>
            <div class="model-config__head">
              <span class="name">{{ p.label }}</span>
              <el-tag size="small" :type="statusOf(p).type" effect="light">{{ statusOf(p).text }}</el-tag>
              <span class="model">{{ p.model_name }}</span>
              <span v-if="p.source === 'page'" class="source">页面配置</span>
              <span v-else-if="p.source === 'env'" class="source">来自 .env</span>
            </div>
          </template>

          <el-form label-width="96px" class="model-config__form" @submit.prevent>
            <el-form-item label="API Key">
              <el-input
                v-model="p.draft_key"
                type="password"
                show-password
                autocomplete="new-password"
                :placeholder="p.has_key ? `已保存 ${p.key_masked}，留空则不修改` : 'sk-...'"
                :disabled="!canEdit"
              />
              <div class="hint">
                在
                <a :href="p.key_url" target="_blank" rel="noopener">{{ p.label }} 控制台</a>
                创建 API Key。{{ p.hint }}
              </div>
            </el-form-item>
            <el-form-item label="API Base">
              <el-input v-model="p.draft_base" :disabled="!canEdit" placeholder="https://api.deepseek.com/v1" />
            </el-form-item>
            <el-form-item label="模型名">
              <el-input v-model="p.draft_model" :disabled="!canEdit" placeholder="deepseek-chat" />
            </el-form-item>

            <el-form-item>
              <el-button :loading="testing === p.provider" :disabled="!canEdit" @click="onTest(p)">
                测试连接
              </el-button>
              <el-button
                type="primary"
                :loading="saving === p.provider"
                :disabled="!canEdit"
                @click="onSave(p)"
              >
                保存并启用
              </el-button>
              <el-button v-if="p.source === 'page'" link type="danger" :disabled="!canEdit" @click="onReset(p)">
                清除页面配置
              </el-button>
              <el-tag v-if="!canEdit" size="small" type="info" class="readonly">只读：账号已禁用</el-tag>
            </el-form-item>

            <el-form-item v-if="tests[p.provider]" label=" ">
              <el-alert
                :type="tests[p.provider]!.ok ? 'success' : 'error'"
                :closable="false"
                show-icon
                :title="tests[p.provider]!.message"
              >
                <template v-if="tests[p.provider]!.latency_ms" #default>
                  <span class="latency">耗时 {{ tests[p.provider]!.latency_ms }} ms</span>
                </template>
              </el-alert>
            </el-form-item>
            <el-form-item v-else-if="p.last_test_message" label="上次测试">
              <span :class="['last-test', p.last_test_ok ? 'last-test--ok' : 'last-test--bad']">
                {{ p.last_test_message }}
              </span>
            </el-form-item>
          </el-form>
        </el-collapse-item>
      </el-collapse>

      <p class="model-config__footer-tip">
        保存后立即生效，无需重启后端；模型下拉里的状态会在几秒内刷新为「可用」。
        这是<b>全站共享</b>的配置：谁保存谁生效，所有用户（含学生）都会使用这个 Key。
      </p>
    </div>

    <template #footer>
      <el-button @click="close(false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 模型配置对话框
 * - 三家服务商（DeepSeek / 通义千问 / 腾讯混元）各自可填 API Key、API Base、模型名
 * - 支持「测试连接」真实校验 Key，保存后即时生效（后端下发到 llm_router）
 */
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { agentApi, type ModelConfigResponse, type ModelProviderConfig } from '@/services/agent'

interface Props {
  modelValue: boolean
}
defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'changed'): void
}>()

/** 服务商 + 页面上的草稿值（草稿和已保存值分开，避免互相覆盖） */
interface ProviderRow extends ModelProviderConfig {
  draft_key: string
  draft_base: string
  draft_model: string
}

interface TestResult {
  ok: boolean
  message: string
  latency_ms: number | null
}

const loading = ref(false)
const saving = ref('')
const testing = ref('')
const canEdit = ref(false)
const providers = ref<ProviderRow[]>([])
const active = ref<string[]>(['deepseek'])
const tests = ref<Record<string, TestResult>>({})

function close(value = false): void {
  emit('update:modelValue', value)
}

function statusOf(p: ModelProviderConfig): { text: string; type: 'success' | 'warning' | 'info' } {
  if (!p.configured) return { text: '未配置', type: 'info' }
  if (p.last_test_ok === true) return { text: '已验证可用', type: 'success' }
  if (p.last_test_ok === false) return { text: '测试未通过', type: 'warning' }
  return { text: '已配置（未验证）', type: 'warning' }
}

/** 用接口数据重建行，草稿值重置为当前保存值 */
function applyData(data: ModelConfigResponse): void {
  providers.value = data.providers.map((p) => ({
    ...p,
    draft_key: '',
    draft_base: p.api_base,
    draft_model: p.model_name,
  }))
  canEdit.value = data.can_edit ?? canEdit.value
}

async function load(): Promise<void> {
  loading.value = true
  tests.value = {}
  try {
    const data = await agentApi.getModelConfig()
    applyData(data)
    // 默认只展开第一个还没配置的服务商，避免三家同时展开把弹窗撑得很长
    const firstUnset = data.providers.find((p) => !p.configured)
    active.value = [firstUnset?.provider || 'deepseek']
  } catch (e: any) {
    ElMessage.error(e?.message || '加载模型配置失败')
  } finally {
    loading.value = false
  }
}

/** 只把用户真正改过的字段发给后端，避免把空 Key 当成清空 */
function payloadOf(p: ProviderRow): Record<string, string> {
  const payload: Record<string, string> = {}
  const key = p.draft_key.trim()
  if (key) payload.api_key = key
  if (p.draft_base.trim() && p.draft_base.trim() !== p.api_base) payload.api_base = p.draft_base.trim()
  if (p.draft_model.trim() && p.draft_model.trim() !== p.model_name) payload.model_name = p.draft_model.trim()
  return payload
}

async function onTest(p: ProviderRow): Promise<void> {
  const payload = payloadOf(p)
  if (!payload.api_key && !p.has_key) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  testing.value = p.provider
  delete tests.value[p.provider]
  try {
    const res = await agentApi.testModelConfig(p.provider, payload)
    tests.value = { ...tests.value, [p.provider]: res }
    if (res.ok) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(res.message)
    }
  } catch (e: any) {
    const msg = e?.message || '测试失败，请检查网络或参数'
    tests.value = { ...tests.value, [p.provider]: { ok: false, message: msg, latency_ms: null } }
    ElMessage.error(msg)
  } finally {
    testing.value = ''
    // 测的是已保存的配置时，后端会记录本次结论，这里把最新状态拉回来
    if (!Object.keys(payload).length) {
      try {
        const data = await agentApi.getModelConfig()
        const drafts = new Map(providers.value.map((x) => [x.provider, x]))
        applyData(data)
        // 保留用户正在编辑的草稿，避免刷新状态把输入清掉
        providers.value.forEach((row) => {
          const old = drafts.get(row.provider)
          if (old) {
            row.draft_key = old.draft_key
            row.draft_base = old.draft_base
            row.draft_model = old.draft_model
          }
        })
      } catch {
        /* 刷新失败不影响本次测试结果的展示 */
      }
    }
  }
}

async function onSave(p: ProviderRow): Promise<void> {
  const payload = payloadOf(p)
  if (!payload.api_key && !p.has_key) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  saving.value = p.provider
  try {
    const res = await agentApi.saveModelConfig(p.provider, payload)
    applyData(res)
    ElMessage.success(`${p.label} 配置已保存并生效`)
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = ''
  }
}

async function onReset(p: ProviderRow): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `清除后 ${p.label} 将回退到 backend/.env 的默认配置，确定继续？`,
      '清除页面配置',
      { type: 'warning', confirmButtonText: '清除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const res = await agentApi.resetModelConfig(p.provider)
    applyData(res)
    ElMessage.success('已恢复为 .env 配置')
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e?.message || '清除失败')
  }
}
</script>

<style scoped lang="scss">
.model-config {
  &__body {
    min-height: 200px;
    max-height: 62vh;
    overflow-y: auto;
    padding-right: 4px;
  }

  &__tip {
    margin-bottom: 12px;
  }

  &__head {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;

    .name {
      font-weight: 600;
      font-size: 14px;
    }
    .model {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
    .source {
      margin-left: auto;
      font-size: 12px;
      color: var(--el-text-color-placeholder);
    }
  }

  &__form {
    padding: 4px 8px 0;
  }

  .hint {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    line-height: 1.6;
    margin-top: 4px;

    a {
      color: var(--el-color-primary);
      text-decoration: none;
    }
  }

  .latency {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .last-test {
    font-size: 12px;

    &--ok {
      color: var(--el-color-success);
    }
    &--bad {
      color: var(--el-color-danger);
    }
  }

  .readonly {
    margin-left: 8px;
  }

  &__footer-tip {
    margin: 8px 0 0;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}
</style>
