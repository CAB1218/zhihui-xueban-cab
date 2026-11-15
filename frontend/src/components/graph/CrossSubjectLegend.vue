<template>
  <el-card shadow="never" class="cross-subject-legend">
    <template #header><span>图例说明</span></template>

    <div class="cross-subject-legend__section">
      <div class="cross-subject-legend__section-title">节点类型</div>
      <div class="cross-subject-legend__special-list">
        <div class="cross-subject-legend__special-item">
          <span class="cross-subject-legend__subject-node">学科</span>
          <span class="cross-subject-legend__special-label">大节点：学科中心</span>
        </div>
        <div class="cross-subject-legend__special-item">
          <span class="cross-subject-legend__knowledge-node" />
          <span class="cross-subject-legend__special-label">小节点：知识点</span>
        </div>
      </div>
    </div>

    <el-divider />

    <!-- 颜色 = 学科 -->
    <div class="cross-subject-legend__section">
      <div class="cross-subject-legend__section-title">学科颜色</div>
      <div class="cross-subject-legend__color-list">
        <div
          v-for="subjId in subjects"
          :key="subjId"
          class="cross-subject-legend__color-item"
        >
          <span
            class="cross-subject-legend__color-dot"
            :style="{ background: subjectColors[subjId] || '#999' }"
          />
          <span class="cross-subject-legend__color-name">
            {{ subjectNameMap[subjId] || subjId }}
          </span>
        </div>
      </div>
    </div>

    <el-divider />

    <!-- 线型 = 关系类型 -->
    <div class="cross-subject-legend__section">
      <div class="cross-subject-legend__section-title">关系类型</div>
      <div class="cross-subject-legend__line-list">
        <div class="cross-subject-legend__line-item">
          <svg width="40" height="12" class="cross-subject-legend__line-svg">
            <line x1="0" y1="6" x2="40" y2="6" stroke="#999" stroke-width="2" />
          </svg>
          <span class="cross-subject-legend__line-label">同学科关系（实线）</span>
        </div>
        <div class="cross-subject-legend__line-item">
          <svg width="40" height="12" class="cross-subject-legend__line-svg">
            <line x1="0" y1="6" x2="40" y2="6" stroke="#E6A23C" stroke-width="2" stroke-dasharray="6,4" />
          </svg>
          <span class="cross-subject-legend__line-label">跨学科关系（虚线）</span>
        </div>
      </div>
    </div>

    <el-divider />

    <!-- 粗细 = 强度 -->
    <div class="cross-subject-legend__section">
      <div class="cross-subject-legend__section-title">关系强度</div>
      <div class="cross-subject-legend__strength-list">
        <div class="cross-subject-legend__strength-item">
          <svg width="40" height="12" class="cross-subject-legend__line-svg">
            <line x1="0" y1="6" x2="40" y2="6" stroke="#67C23A" stroke-width="4" />
          </svg>
          <span class="cross-subject-legend__strength-label">强 (≥0.7)</span>
        </div>
        <div class="cross-subject-legend__strength-item">
          <svg width="40" height="12" class="cross-subject-legend__line-svg">
            <line x1="0" y1="6" x2="40" y2="6" stroke="#E6A23C" stroke-width="2.5" />
          </svg>
          <span class="cross-subject-legend__strength-label">中 (0.4-0.7)</span>
        </div>
        <div class="cross-subject-legend__strength-item">
          <svg width="40" height="12" class="cross-subject-legend__line-svg">
            <line x1="0" y1="6" x2="40" y2="6" stroke="#F56C6C" stroke-width="1" />
          </svg>
          <span class="cross-subject-legend__strength-label">弱 (&lt;0.4)</span>
        </div>
      </div>
    </div>

    <el-divider />

    <!-- 特殊标记 -->
    <div class="cross-subject-legend__section">
      <div class="cross-subject-legend__section-title">特殊标记</div>
      <div class="cross-subject-legend__special-list">
        <div class="cross-subject-legend__special-item">
          <span class="cross-subject-legend__special-icon" style="color: #E6A23C;">⚠</span>
          <span class="cross-subject-legend__special-label">存在常见误解</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 跨学科图例组件
 * 颜色=学科、线型=关系类型、粗细=强度、特殊标记
 */

defineProps<{
  subjects: string[]
  subjectColors: Record<string, string>
  subjectNameMap: Record<string, string>
}>()
</script>

<style lang="scss" scoped>
.cross-subject-legend {
  &__section {
    margin-bottom: 4px;
  }

  &__section-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: 8px;
  }

  &__color-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  &__color-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  &__color-dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  &__color-name {
    color: var(--color-text-primary);
  }

  &__line-list,
  &__strength-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__line-item,
  &__strength-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  &__line-svg {
    flex-shrink: 0;
  }

  &__line-label,
  &__strength-label {
    color: var(--color-text-secondary);
  }

  &__special-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  &__special-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  &__special-icon {
    font-size: 16px;
    font-weight: 700;
  }

  &__subject-node {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #1976d2;
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    flex-shrink: 0;
  }

  &__knowledge-node {
    width: 20px;
    height: 20px;
    margin: 0 8px;
    border-radius: 50%;
    background: #1976d2;
    flex-shrink: 0;
  }

  &__special-label {
    color: var(--color-text-secondary);
  }
}
</style>
