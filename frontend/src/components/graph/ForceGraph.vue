<template>
  <div ref="containerRef" class="force-graph" :style="{ width, height }">
    <svg ref="svgRef" :width="svgWidth" :height="svgHeight">
      <defs>
        <marker
          id="arrowhead"
          markerWidth="7"
          markerHeight="5"
          refX="7"
          refY="2.5"
          orient="auto"
          markerUnits="userSpaceOnUse"
        >
          <polygon points="0 0, 7 2.5, 0 5" fill="#999" />
        </marker>
        <!-- 跨学科关系渐变色定义 -->
        <linearGradient
          v-for="(grad, idx) in crossGradients"
          :key="`grad-${idx}`"
          :id="`cross-grad-${idx}`"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" :stop-color="grad.color1" />
          <stop offset="100%" :stop-color="grad.color2" />
        </linearGradient>
      </defs>

      <g class="links">
        <line
          v-for="(link, idx) in renderedLinks"
          :key="`link-${idx}`"
          :x1="getLinkX(link, 'source', 'x')"
          :y1="getLinkX(link, 'source', 'y')"
          :x2="getLinkX(link, 'target', 'x')"
          :y2="getLinkX(link, 'target', 'y')"
          :stroke="getLinkStroke(link, idx)"
          :stroke-width="getLinkWidth(link)"
          :stroke-dasharray="getLinkDashArray(link)"
          :marker-end="link.type !== 'RELATED' ? 'url(#arrowhead)' : ''"
          class="link-line"
          @click.stop="onLinkClick(link)"
        />
      </g>

      <g class="nodes">
        <g
          v-for="node in renderedNodes"
          :key="node.id"
          :transform="`translate(${node.x || 0}, ${node.y || 0})`"
          class="node-group"
          @mousedown.prevent="onNodeDragStart($event, node)"
          @mouseenter="onNodeHover(node, $event)"
          @mouseleave="onNodeLeave"
          @click="onNodeClick(node)"
        >
          <circle
            :r="getNodeRadius(node)"
            :fill="getNodeColor(node)"
            :stroke="getNodeStroke(node)"
            :stroke-width="getNodeStrokeWidth(node)"
            class="node-circle"
          />
          <text
            v-if="node.node_type === 'subject'"
            dy="4"
            text-anchor="middle"
            fill="#fff"
            :font-size="(node.name || '').length > 4 ? 9 : 11"
            font-weight="700"
            class="node-type-label"
          >
            {{ node.name || node.subject_id || '学科' }}
          </text>
          <!-- Misconception 小图标（跨学科模式） -->
          <text
            v-if="crossSubjectMode && node.has_misconception"
            :dy="-(getNodeRadius(node) + 4)"
            text-anchor="middle"
            font-size="14"
            fill="#E6A23C"
            class="node-warning-icon"
          >
            ⚠
          </text>
          <text
            v-if="node.node_type !== 'subject'"
            text-anchor="middle"
            fill="#fff"
            font-size="11"
            font-weight="600"
            class="node-label"
          >
            <tspan
              v-for="(line, lineIndex) in getNodeLabelLines(node)"
              :key="`${node.id}-label-${lineIndex}`"
              x="0"
              :dy="lineIndex === 0 ? (getNodeLabelLines(node).length === 1 ? 4 : -2) : 14"
            >
              {{ line }}
            </tspan>
          </text>
        </g>
      </g>
    </svg>

    <!-- Tooltip -->
    <div v-if="hoveredNode" class="force-graph__tooltip" :style="tooltipStyle">
      <strong>{{ hoveredNode.name || hoveredNode.id }}</strong>
      <p v-if="hoveredNode.description">{{ hoveredNode.description }}</p>
      <p v-if="hoveredNode.subject">学科: {{ subjectNameMap[hoveredNode.subject] || hoveredNode.subject }}</p>
      <p v-if="hoveredNode.has_misconception" style="color: #E6A23C;">⚠ 存在常见误解标注</p>
    </div>

    <!-- 缩放控制 -->
    <div class="force-graph__controls">
      <el-button size="small" circle @click="zoomIn">
        <el-icon><ZoomIn /></el-icon>
      </el-button>
      <el-button size="small" circle @click="zoomOut">
        <el-icon><ZoomOut /></el-icon>
      </el-button>
      <el-button size="small" circle @click="resetView">
        <el-icon><FullScreen /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AI4EDU 力导向图组件（自定义 SVG 实现，不依赖 D3）
 * 支持：拖拽/缩放/hover tooltip/节点点击/关系点击
 * 跨学科模式：虚线+渐变色连线、学科聚合力、misconception节点橙色边框
 */
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { ZoomIn, ZoomOut, FullScreen } from '@element-plus/icons-vue'
import type { GraphNode, GraphLink } from '@/services/graph'

const props = withDefaults(defineProps<{
  nodes: GraphNode[]
  links: GraphLink[]
  width?: string
  height?: string
  crossSubjectMode?: boolean
  subjectColors?: Record<string, string>
  selectedNodeId?: string | null
}>(), {
  width: '100%',
  height: '600px',
  crossSubjectMode: false,
  subjectColors: () => ({}),
  selectedNodeId: null,
})

const emit = defineEmits<{
  (e: 'node-click', node: GraphNode): void
  (e: 'node-hover', node: GraphNode | null): void
  (e: 'link-click', link: GraphLink): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const svgRef = ref<SVGSVGElement | null>(null)

const svgWidth = ref(800)
const svgHeight = ref(600)
const hoveredNode = ref<GraphNode | null>(null)
const tooltipPos = ref({ x: 0, y: 0 })

// 渲染用节点（包含位置信息）
const renderedNodes = ref<GraphNode[]>([])
const renderedLinks = ref<GraphLink[]>([])

// 缩放状态
const currentScale = ref(1)
const currentTranslate = ref({ x: 0, y: 0 })

// 拖拽状态
let dragNode: GraphNode | null = null

// 学科颜色映射（可被 props 覆盖）
const defaultSubjectColors: Record<string, string> = {
  math: '#1976D2',
  physics: '#F57C00',
  chemistry: '#4CAF50',
  biology: '#388E3C',
  cs: '#7B1FA2',
  chinese: '#D32F2F',
  english: '#00796B',
  history: '#5D4037',
  geography: '#0288D1',
  politics: '#C62828',
  pe: '#FF6F00',
  art: '#AD1457',
}

const subjectNameMap: Record<string, string> = {
  math: '数学', physics: '物理学', chemistry: '化学', biology: '生物学',
  cs: '计算机科学', chinese: '语文', english: '英语', history: '历史',
  geography: '地理', politics: '政治', pe: '体育', art: '艺术',
}

// 合并默认颜色和传入颜色
const mergedColors = computed(() => ({ ...defaultSubjectColors, ...props.subjectColors }))

// 跨学科关系渐变色定义
const crossGradients = computed(() => {
  const grads: Array<{ color1: string; color2: string }> = []
  for (const link of renderedLinks.value) {
    if (!link.is_cross) continue
    const srcNode = findNode(link.source)
    const tgtNode = findNode(link.target)
    grads.push({
      color1: mergedColors.value[srcNode?.subject || ''] || '#5B8FF9',
      color2: mergedColors.value[tgtNode?.subject || ''] || '#5B8FF9',
    })
  }
  return grads
})

const tooltipStyle = computed(() => ({
  left: `${tooltipPos.value.x + 15}px`,
  top: `${tooltipPos.value.y - 10}px`,
}))

function findNode(ref: string | GraphNode): GraphNode | undefined {
  if (typeof ref === 'object' && ref !== null) return ref as GraphNode
  return renderedNodes.value.find((n) => n.id === ref)
}

function getNodeRadius(node: GraphNode): number {
  if (node.node_type === 'subject') return 34
  const linkCount = props.links.filter(
    (l) => (l.source === node.id || l.source === node) || (l.target === node.id || l.target === node)
  ).length
  return Math.max(28, Math.min(40, 20 + linkCount * 2))
}

function getNodeColor(node: GraphNode): string {
  if (node.node_type !== 'subject' && props.selectedNodeId === node.id) return '#A8ABB2'
  if (node.color) return node.color
  return mergedColors.value[node.subject || node.subject_id || ''] || '#5B8FF9'
}

function getNodeStroke(node: GraphNode): string {
  if (node.node_type === 'subject') return getNodeColor(node)
  if (node.has_misconception) return '#E6A23C'
  return '#fff'
}

function getNodeStrokeWidth(node: GraphNode): number {
  if (node.node_type === 'subject') return 5
  if (node.has_misconception) return 3
  return 2
}

function getLinkStroke(link: GraphLink, _idx: number): string {
  if (link.type === 'HAS_KNOWLEDGE') {
    const sourceNode = findNode(link.source)
    return sourceNode ? getNodeColor(sourceNode) : '#5B8FF9'
  }
  if (props.crossSubjectMode && link.is_cross) {
    return `url(#cross-grad-${getCrossGradientIndex(link)})`
  }
  if (props.crossSubjectMode && link.strength !== undefined) {
    if (link.strength >= 0.7) return '#666'
    if (link.strength >= 0.4) return '#999'
    return '#ccc'
  }
  return '#ccc'
}

function getCrossGradientIndex(link: GraphLink): number {
  let count = 0
  for (const l of renderedLinks.value) {
    if (l === link) return count
    if (l.is_cross) count++
  }
  return 0
}

function getLinkWidth(link: GraphLink): number {
  if (link.type === 'HAS_KNOWLEDGE') return 3
  if (link.strength !== undefined) {
    if (link.is_cross) return 1 + link.strength * 4
    return 1 + link.strength * 3
  }
  return 1.5
}

function getLinkDashArray(link: GraphLink): string {
  if (props.crossSubjectMode && link.is_cross) {
    return '6,4'
  }
  return 'none'
}

function getLinkX(link: GraphLink, end: 'source' | 'target', axis: 'x' | 'y'): number {
  const val = link[end]
  if (typeof val === 'object' && val !== null) {
    return (val as GraphNode)[axis] || 0
  }
  const node = renderedNodes.value.find((n) => n.id === val)
  return node?.[axis] || 0
}

function getNodeLabelLines(node: GraphNode): string[] {
  const label = node.name || node.id
  if (label.length <= 4) return [label]

  const compactLabel = label.length > 8 ? `${label.slice(0, 7)}…` : label
  const splitAt = Math.ceil(compactLabel.length / 2)
  return [compactLabel.slice(0, splitAt), compactLabel.slice(splitAt)]
}

// ==================== 力导向布局（简化版） ====================

let animationFrameId: number | null = null

function initLayout(): void {
  if (props.nodes.length === 0) {
    renderedNodes.value = []
    renderedLinks.value = []
    return
  }

  const cx = svgWidth.value / 2
  const cy = svgHeight.value / 2

  // 初始化节点位置（跨学科模式按学科分组初始化）
  const subjectGroups: Record<string, number[]> = {}
  if (props.crossSubjectMode) {
    props.nodes.forEach((n, i) => {
      const subj = n.subject || 'default'
      if (!subjectGroups[subj]) subjectGroups[subj] = []
      subjectGroups[subj].push(i)
    })
  }

  const nodes = props.nodes.map((n, i) => {
    let initX: number, initY: number

    if (props.crossSubjectMode) {
      // 每个学科中心节点占据一个分组中心，知识点环绕所属学科。
      const subjects = Object.keys(subjectGroups)
      const subjIdx = subjects.indexOf(n.subject || 'default')
      const subjCount = subjects.length
      const groupAngle = (2 * Math.PI * subjIdx) / subjCount
      const groupRadius = Math.min(svgWidth.value, svgHeight.value) * 0.28
      const groupX = cx + groupRadius * Math.cos(groupAngle)
      const groupY = cy + groupRadius * Math.sin(groupAngle)

      if (n.node_type === 'subject') {
        initX = groupX
        initY = groupY
      } else {
        const knowledgeIndexes = (subjectGroups[n.subject || 'default'] || [])
          .filter((idx) => props.nodes[idx]?.node_type !== 'subject')
        const withinGroupIdx = Math.max(0, knowledgeIndexes.indexOf(i))
        const withinAngle = (2 * Math.PI * withinGroupIdx) / Math.max(knowledgeIndexes.length, 1)
        const localRadius = 90
        initX = groupX + localRadius * Math.cos(withinAngle)
        initY = groupY + localRadius * Math.sin(withinAngle)
      }
    } else if (n.node_type === 'subject') {
      initX = cx
      initY = cy
    } else {
      const angle = (2 * Math.PI * i) / props.nodes.length
      const r = Math.min(svgWidth.value, svgHeight.value) * 0.3
      initX = cx + r * Math.cos(angle)
      initY = cy + r * Math.sin(angle)
    }

    return {
      ...n,
      x: n.x ?? initX,
      y: n.y ?? initY,
      vx: 0,
      vy: 0,
    }
  })

  const links = props.links.map((l) => ({
    ...l,
    source: typeof l.source === 'object' ? (l.source as GraphNode).id : l.source,
    target: typeof l.target === 'object' ? (l.target as GraphNode).id : l.target,
  }))

  renderedNodes.value = nodes
  renderedLinks.value = links

  runSimulation(nodes, links)
}

function runSimulation(nodes: GraphNode[], links: GraphLink[]): void {
  const iterations = 120
  const alpha = 0.3
  const cx = svgWidth.value / 2
  const cy = svgHeight.value / 2

  for (let iter = 0; iter < iterations; iter++) {
    const currentAlpha = alpha * (1 - iter / iterations)

    // 斥力
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = (nodes[j].x || 0) - (nodes[i].x || 0)
        const dy = (nodes[j].y || 0) - (nodes[i].y || 0)
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = 5000 / (dist * dist)
        const fx = (dx / dist) * force * currentAlpha
        const fy = (dy / dist) * force * currentAlpha

        if (!isDragging(nodes[i])) {
          nodes[i].x = (nodes[i].x || 0) - fx
          nodes[i].y = (nodes[i].y || 0) - fy
        }
        if (!isDragging(nodes[j])) {
          nodes[j].x = (nodes[j].x || 0) + fx
          nodes[j].y = (nodes[j].y || 0) + fy
        }
      }
    }

    // 引力（边）
    for (const link of links) {
      const sourceNode = nodes.find((n) => n.id === link.source)
      const targetNode = nodes.find((n) => n.id === link.target)
      if (!sourceNode || !targetNode) continue

      const dx = (targetNode.x || 0) - (sourceNode.x || 0)
      const dy = (targetNode.y || 0) - (sourceNode.y || 0)
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const force = (dist - 100) * 0.01 * currentAlpha
      const fx = (dx / dist) * force
      const fy = (dy / dist) * force

      if (!isDragging(sourceNode)) {
        sourceNode.x = (sourceNode.x || 0) + fx
        sourceNode.y = (sourceNode.y || 0) + fy
      }
      if (!isDragging(targetNode)) {
        targetNode.x = (targetNode.x || 0) - fx
        targetNode.y = (targetNode.y || 0) - fy
      }
    }

    // 跨学科模式：学科聚合力（同学科节点间额外引力 30%）
    if (props.crossSubjectMode) {
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          if (nodes[i].subject === nodes[j].subject && nodes[i].subject) {
            const dx = (nodes[j].x || 0) - (nodes[i].x || 0)
            const dy = (nodes[j].y || 0) - (nodes[i].y || 0)
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            // 同学科吸引力：距离远时拉近，距离近时排斥
            const force = (dist - 80) * 0.003 * currentAlpha
            const fx = (dx / dist) * force
            const fy = (dy / dist) * force

            if (!isDragging(nodes[i])) {
              nodes[i].x = (nodes[i].x || 0) + fx
              nodes[i].y = (nodes[i].y || 0) + fy
            }
            if (!isDragging(nodes[j])) {
              nodes[j].x = (nodes[j].x || 0) - fx
              nodes[j].y = (nodes[j].y || 0) - fy
            }
          }
        }
      }
    }

    // 向心力
    for (const node of nodes) {
      if (isDragging(node)) continue
      const centerStrength = node.node_type === 'subject' && !props.crossSubjectMode ? 0.2 : 0.01
      node.x = (node.x || 0) + (cx - (node.x || 0)) * centerStrength * currentAlpha
      node.y = (node.y || 0) + (cy - (node.y || 0)) * centerStrength * currentAlpha
    }
  }

  renderedNodes.value = [...nodes]
}

function isDragging(_node: GraphNode): boolean {
  return dragNode?.id === _node.id
}

// ==================== 交互 ====================

function onNodeDragStart(event: MouseEvent, node: GraphNode): void {
  dragNode = node
  const startX = event.clientX
  const startY = event.clientY
  const origX = node.x || 0
  const origY = node.y || 0

  function onMouseMove(e: MouseEvent): void {
    if (!dragNode) return
    const dx = (e.clientX - startX) / currentScale.value
    const dy = (e.clientY - startY) / currentScale.value
    dragNode.x = origX + dx
    dragNode.y = origY + dy
    renderedNodes.value = [...renderedNodes.value]
  }

  function onMouseUp(): void {
    dragNode = null
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

function onNodeHover(node: GraphNode, event?: MouseEvent): void {
  hoveredNode.value = node
  if (event && containerRef.value) {
    const rect = containerRef.value.getBoundingClientRect()
    tooltipPos.value = { x: event.clientX - rect.left, y: event.clientY - rect.top }
  }
  emit('node-hover', node)
}

function onNodeLeave(): void {
  hoveredNode.value = null
  emit('node-hover', null)
}

function onNodeClick(node: GraphNode): void {
  emit('node-click', node)
}

function onLinkClick(link: GraphLink): void {
  emit('link-click', link)
}

function zoomIn(): void {
  currentScale.value = Math.min(currentScale.value * 1.2, 4)
  applyTransform()
}

function zoomOut(): void {
  currentScale.value = Math.max(currentScale.value / 1.2, 0.25)
  applyTransform()
}

function resetView(): void {
  currentScale.value = 1
  currentTranslate.value = { x: 0, y: 0 }
  applyTransform()
}

function applyTransform(): void {
  if (svgRef.value) {
    const g = svgRef.value.querySelector('.links') as SVGGElement
    const gNodes = svgRef.value.querySelector('.nodes') as SVGGElement
    const transform = `translate(${currentTranslate.value.x}, ${currentTranslate.value.y}) scale(${currentScale.value})`
    if (g) g.setAttribute('transform', transform)
    if (gNodes) gNodes.setAttribute('transform', transform)
  }
}

function updateSize(): void {
  if (containerRef.value) {
    svgWidth.value = containerRef.value.clientWidth
    svgHeight.value = containerRef.value.clientHeight
  }
}

// 监听数据变化重新布局
watch(
  () => [props.nodes, props.links],
  () => {
    initLayout()
  },
  { deep: true },
)

onMounted(() => {
  updateSize()
  initLayout()
  window.addEventListener('resize', updateSize)
})

onUnmounted(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  window.removeEventListener('resize', updateSize)
})
</script>

<style lang="scss" scoped>
.force-graph {
  position: relative;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--border-radius-md);
  overflow: hidden;

  svg {
    display: block;
  }

  .node-circle {
    cursor: grab;
    transition: r 0.15s ease;

    &:hover {
      stroke-width: 3;
      stroke: var(--color-info);
    }
  }

  .node-label {
    pointer-events: none;
    user-select: none;
  }

  .node-type-label {
    pointer-events: none;
    user-select: none;
  }

  .node-warning-icon {
    pointer-events: none;
    user-select: none;
  }

  .link-line {
    cursor: pointer;
    transition: stroke-width 0.15s ease;

    &:hover {
      stroke-width: 4;
    }
  }

  &__tooltip {
    position: absolute;
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.8);
    color: #fff;
    border-radius: var(--border-radius-sm);
    font-size: 13px;
    max-width: 250px;
    pointer-events: none;
    z-index: 100;

    strong {
      display: block;
      margin-bottom: 4px;
    }

    p {
      margin: 2px 0;
      font-size: 12px;
      color: #ccc;
    }
  }

  &__controls {
    position: absolute;
    bottom: 12px;
    right: 12px;
    display: flex;
    gap: 4px;
  }
}
</style>
