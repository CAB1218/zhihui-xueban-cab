<template>
  <div class="not-found">
    <div class="not-found__card">
      <div class="not-found__code">404</div>
      <h2 class="not-found__title">页面不存在</h2>
      <p class="not-found__desc">
        没有找到地址 <code>{{ attemptedPath }}</code> 对应的页面。<br />
        可能是链接少了一段路径，或者地址拼写有误。
      </p>

      <div class="not-found__suggest">
        <p class="not-found__suggest-title">你要找的可能是：</p>
        <router-link class="not-found__link" :to="dashboardPath">场景首页（仪表盘）</router-link>
        <router-link class="not-found__link" :to="analysisPath">学情分析</router-link>
        <router-link class="not-found__link" :to="curriculumPath">课程梳理</router-link>
      </div>

      <div class="not-found__actions">
        <el-button type="primary" @click="goBack">返回上一页</el-button>
        <el-button @click="goDashboard">回到仪表盘</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 404 页面
 * 之前这里直接复用了场景仪表盘组件，导致用户看到「页面不存在」标题
 * 却渲染出课堂模式数据，容易误以为数据丢失。改为独立的提示页，并给出可用入口。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

/** 用户实际访问的地址，原样回显便于自查 */
const attemptedPath = computed(() => route.fullPath)

/** 从地址中推断场景前缀，兜底 classroom */
const scenePrefix = computed(() => {
  const m = route.path.match(/^\/scene\/([^/]+)/)
  const candidate = m ? m[1] : 'classroom'
  return ['classroom', 'self_study', 'exam', 'discussion'].includes(candidate) ? candidate : 'classroom'
})

const dashboardPath = computed(() => `/scene/${scenePrefix.value}/dashboard`)
const analysisPath = computed(() => `/scene/${scenePrefix.value}/analysis`)
const curriculumPath = computed(() => `/scene/${scenePrefix.value}/curriculum`)

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push(dashboardPath.value)
  }
}

function goDashboard() {
  router.push(dashboardPath.value)
}
</script>

<style lang="scss" scoped>
.not-found {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  padding: 24px;

  &__card {
    width: 100%;
    max-width: 560px;
    background: #fff;
    border-radius: 16px;
    padding: 40px 36px;
    box-shadow: 0 6px 28px rgba(0, 0, 0, 0.08);
    text-align: center;
  }

  &__code {
    font-size: 64px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: 2px;
    background: linear-gradient(135deg, #409eff, #6f7ad3);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  &__title {
    margin: 16px 0 10px;
    font-size: 22px;
    color: #303133;
  }

  &__desc {
    margin: 0 0 24px;
    font-size: 14px;
    line-height: 1.7;
    color: #909399;
    word-break: break-all;

    code {
      padding: 2px 6px;
      border-radius: 4px;
      background: #f2f3f5;
      color: #606266;
      font-family: Consolas, Monaco, monospace;
    }
  }

  &__suggest {
    text-align: left;
    padding: 16px 18px;
    border-radius: 10px;
    background: #f7f9fc;
    margin-bottom: 24px;
  }

  &__suggest-title {
    margin: 0 0 10px;
    font-size: 13px;
    color: #606266;
  }

  &__link {
    display: inline-block;
    margin: 0 12px 8px 0;
    font-size: 14px;
    color: #409eff;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  &__actions {
    display: flex;
    gap: 12px;
    justify-content: center;
  }
}
</style>
