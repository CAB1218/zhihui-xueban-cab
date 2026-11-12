<template>
  <div class="settings-view">
    <div class="page-header">
      <div class="page-header__left">
        <h2>偏好设置</h2>
        <span class="page-header__hint">外观、侧边栏与默认进入的场景；保存后跨设备生效</span>
      </div>
      <div class="page-header__actions">
        <el-button :icon="Back" @click="goBack">返回</el-button>
      </div>
    </div>

    <el-card shadow="never" class="card-block">
      <template #header>
        <div class="card-header">
          <span class="title">界面外观</span>
          <span class="sub">切换即时预览，点「保存设置」后长期生效</span>
        </div>
      </template>

      <div class="theme-options">
        <div
          v-for="opt in themeOptions"
          :key="opt.value"
          class="theme-card"
          :class="{ 'theme-card--active': form.theme === opt.value }"
          @click="previewTheme(opt.value)"
        >
          <div class="theme-card__preview" :class="`theme-card__preview--${opt.value}`">
            <span class="theme-card__bar" />
            <span class="theme-card__line" />
            <span class="theme-card__line theme-card__line--short" />
          </div>
          <div class="theme-card__label">
            <el-icon v-if="form.theme === opt.value" class="theme-card__check"><Check /></el-icon>
            <span>{{ opt.label }}</span>
          </div>
        </div>
      </div>

      <p class="hint-line">当前主题：{{ currentThemeLabel }}（保存在账号偏好里，换电脑登录同样生效）</p>
    </el-card>

    <el-card shadow="never" class="card-block">
      <template #header>
        <div class="card-header"><span class="title">布局与进入方式</span></div>
      </template>

      <el-form label-width="140px" class="pref-form" @submit.prevent>
        <el-form-item label="侧边栏默认折叠">
          <el-switch v-model="form.sidebarCollapsed" />
          <span class="field-tip">开启后进入页面时侧边栏收起，只显示图标；内容区更宽</span>
        </el-form-item>
        <el-form-item label="默认进入的场景">
          <el-select v-model="form.defaultScene" style="width: 200px">
            <el-option v-for="s in SCENE_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
          <span class="field-tip">登录后访问首页时直接打开该场景的仪表盘</span>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="card-block">
      <template #header>
        <div class="card-header"><span class="title">账号偏好随设备同步</span></div>
      </template>
      <el-descriptions :column="1" size="small" border>
        <el-descriptions-item label="同步方式">
          偏好保存在账号上（users.preferences 字段），登录任意设备后自动回填
        </el-descriptions-item>
        <el-descriptions-item label="本地缓存">
          同时写入浏览器缓存，未登录或断网时仍保留上次选择
        </el-descriptions-item>
        <el-descriptions-item label="恢复方式">
          点下方「恢复默认」后保存，即可回到浅色 + 侧边栏展开 + 课堂模式
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <div class="save-bar">
      <el-button @click="resetDefaults" :disabled="saving">恢复默认</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 偏好设置
 * 头像菜单「偏好设置」落地页：主题 / 侧边栏 / 默认场景
 * 本地写 userStore + localStorage，同时 PUT /users/{id}/preferences 落到账号
 */
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Check } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useUserStore, type UserPreferences } from '@/stores/user'
import { userApi } from '@/services/user'
import { SCENE_OPTIONS, toServerPayload } from '@/utils/preferences'
import { applyTheme, type ThemeMode } from '@/utils/theme'

const router = useRouter()
const authStore = useAuthStore()
const userStore = useUserStore()

const saving = ref(false)

const themeOptions: Array<{ value: ThemeMode; label: string }> = [
  { value: 'light', label: '浅色' },
  { value: 'dark', label: '深色' },
  { value: 'auto', label: '跟随系统' },
]

const form = reactive({
  theme: userStore.preferences.theme as ThemeMode,
  sidebarCollapsed: userStore.preferences.sidebarCollapsed,
  defaultScene: userStore.preferences.defaultScene,
})

const currentThemeLabel = computed(
  () => themeOptions.find((t) => t.value === form.theme)?.label ?? '浅色',
)

function previewTheme(theme: ThemeMode): void {
  form.theme = theme
  applyTheme(theme)
}

async function save(): Promise<void> {
  const uid = authStore.user?.id
  saving.value = true
  try {
    const patch: Partial<UserPreferences> = {
      theme: form.theme,
      sidebarCollapsed: form.sidebarCollapsed,
      defaultScene: form.defaultScene,
    }
    userStore.updatePreferences(patch)
    applyTheme(form.theme)

    if (uid) {
      await userApi.updatePreferences(uid, toServerPayload(userStore.preferences))
    }
    ElMessage.success('偏好设置已保存')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

function resetDefaults(): void {
  form.theme = 'light'
  form.sidebarCollapsed = false
  form.defaultScene = 'classroom'
  applyTheme('light')
  ElMessage.info('已恢复默认值，点「保存设置」后生效')
}

function goBack(): void {
  if (window.history.length > 1) router.back()
  else router.push('/')
}
</script>

<style lang="scss" scoped>
.settings-view {
  padding: 4px 0 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 14px;

  &__left {
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-wrap: wrap;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
      white-space: nowrap;
    }
  }

  &__hint {
    font-size: 12px;
    color: var(--color-text-secondary);
  }
}

.card-block {
  margin-bottom: 14px;
}

.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;

  .title {
    font-weight: 600;
  }

  .sub {
    font-size: 12px;
    color: var(--color-text-secondary);
  }
}

.theme-options {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.theme-card {
  width: 148px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  background: var(--color-bg-primary);

  &:hover {
    border-color: var(--scene-primary-color, #1976d2);
  }

  &--active {
    border-color: var(--scene-primary-color, #1976d2);
    box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.15);
  }

  &__preview {
    height: 74px;
    border-radius: 6px;
    border: 1px solid var(--color-border-light);
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;

    &--light {
      background: #ffffff;
    }

    &--dark {
      background: #1b1e23;
      border-color: #333940;
    }

    &--auto {
      background: linear-gradient(90deg, #ffffff 50%, #1b1e23 50%);
    }
  }

  &__bar {
    display: block;
    height: 8px;
    border-radius: 3px;
    background: var(--scene-primary-color, #1976d2);
    opacity: 0.85;
  }

  &__line {
    display: block;
    height: 6px;
    border-radius: 3px;
    background: rgba(128, 128, 128, 0.35);

    &--short {
      width: 60%;
    }
  }

  &__label {
    margin-top: 8px;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  &__check {
    color: var(--scene-primary-color, #1976d2);
  }
}

.hint-line {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.pref-form {
  max-width: 640px;

  :deep(.el-form-item) {
    margin-bottom: 16px;
  }
}

.field-tip {
  margin-left: 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.save-bar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
