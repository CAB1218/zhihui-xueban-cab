<template>
  <div
    class="misconception-badge"
    @mouseenter="showTooltip = true"
    @mouseleave="showTooltip = false"
    @click.stop="$emit('open-dialog')"
  >
    <el-icon :size="14" color="#fff"><Warning /></el-icon>

    <!-- Tooltip: 显示前3条误解摘要 -->
    <div v-if="showTooltip && misconceptions.length > 0" class="misconception-badge__tooltip">
      <div class="misconception-badge__tooltip-title">
        ⚠ {{ misconceptions.length }} 个常见误解
      </div>
      <div
        v-for="(mc, idx) in previewList"
        :key="mc.mc_id"
        class="misconception-badge__tooltip-item"
      >
        <span class="misconception-badge__tooltip-index">{{ idx + 1 }}.</span>
        <span class="misconception-badge__tooltip-text">{{ mc.misconception }}</span>
      </div>
      <div v-if="misconceptions.length > 3" class="misconception-badge__tooltip-more">
        点击查看全部...
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 Misconception 标注角标组件
 * 橙色圆形 Warning 图标，hover 显示误解摘要 tooltip，click 打开详情弹窗
 */
import { ref, computed } from 'vue'
import { Warning } from '@element-plus/icons-vue'
import type { Misconception } from '@/services/graph'

const props = defineProps<{
  misconceptions: Misconception[]
}>()

defineEmits<{
  (e: 'open-dialog'): void
}>()

const showTooltip = ref<boolean>(false)

/** tooltip 中预览的前3条误解 */
const previewList = computed(() => props.misconceptions.slice(0, 3))
</script>

<style lang="scss" scoped>
.misconception-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e6a23c;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  box-shadow: 0 2px 6px rgba(230, 162, 60, 0.4);
  transition: transform 0.15s ease;

  &:hover {
    transform: scale(1.15);
  }

  &__tooltip {
    position: absolute;
    top: 28px;
    right: 0;
    width: 280px;
    padding: 10px 12px;
    background: rgba(0, 0, 0, 0.85);
    color: #fff;
    border-radius: 6px;
    font-size: 12px;
    z-index: 200;
    pointer-events: none;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }

  &__tooltip-title {
    font-weight: 600;
    margin-bottom: 6px;
    color: #e6a23c;
  }

  &__tooltip-item {
    display: flex;
    gap: 4px;
    margin-bottom: 4px;
    line-height: 1.4;
  }

  &__tooltip-index {
    flex-shrink: 0;
    color: #ccc;
  }

  &__tooltip-text {
    color: #f0c0c0;
  }

  &__tooltip-more {
    margin-top: 4px;
    color: #409eff;
    font-style: italic;
  }
}
</style>
