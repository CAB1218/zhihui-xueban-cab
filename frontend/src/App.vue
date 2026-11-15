<template>
  <!-- 错误边界：子组件崩溃时显示友好提示 -->
  <div v-if="hasError" class="error-boundary">
    <div class="error-boundary__content">
      <el-icon :size="64" color="#F56C6C"><WarningFilled /></el-icon>
      <h2>页面加载出错</h2>
      <p>{{ errorMessage }}</p>
      <div class="error-boundary__actions">
        <el-button type="primary" @click="handleReload">刷新页面</el-button>
        <el-button @click="handleClearAndReload">清除缓存并重新登录</el-button>
      </div>
      <p class="error-boundary__tip">如果问题持续存在，请按 F12 打开控制台查看详细错误信息</p>
    </div>
  </div>

  <template v-else>
    <OfflineAlert />
    <router-view />
  </template>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 根组件
 * 包含离线提示和路由视图，所有页面通过 router-view 渲染
 * 内置错误边界，防止白屏
 */
import { ref, onErrorCaptured } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'
import OfflineAlert from '@/components/common/OfflineAlert.vue'

const hasError = ref(false)
const errorMessage = ref('')

onErrorCaptured((err: Error, _vm, _info) => {
  console.error('[ErrorBoundary] 组件渲染错误:', err, _info)
  hasError.value = true
  errorMessage.value = err.message || '未知错误'
  return false // 阻止错误继续向上传播
})

function handleReload() {
  hasError.value = false
  window.location.reload()
}

function handleClearAndReload() {
  localStorage.clear()
  sessionStorage.clear()
  window.location.href = '/'
}
</script>

<style lang="scss">
#app {
  width: 100%;
  height: 100%;
}

.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f5f7fa;

  &__content {
    text-align: center;
    padding: 40px;
    max-width: 480px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  }

  h2 {
    margin: 16px 0 8px;
    font-size: 20px;
    color: #303133;
  }

  p {
    color: #909399;
    margin-bottom: 8px;
    font-size: 14px;
  }

  &__actions {
    display: flex;
    gap: 12px;
    justify-content: center;
    margin: 24px 0 16px;
  }

  &__tip {
    font-size: 12px;
    color: #c0c4cc;
  }
}
</style>
