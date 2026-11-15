/**
 * 智慧学伴 知识图谱 Store
 * 管理图谱广场统计、节点详情、邻居数据、misconception、跨学科、任务
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { graphApi } from '@/services/graph'
import type {
  SquareStat,
  KnowledgeNode,
  NeighborData,
  CognitiveGoal,
  Misconception,
  MisconceptionInput,
  MisconceptionSuggestion,
  NodeTask,
  CrossSubjectResponse,
} from '@/services/graph'

export const useGraphStore = defineStore('graph', () => {
  // ============ State ============

  /** 图谱广场统计 */
  const squareStats = ref<SquareStat[]>([])
  /** 当前节点详情 */
  const currentGraph = ref<KnowledgeNode | null>(null)
  /** 邻居节点数据 */
  const neighborNodes = ref<NeighborData>({ nodes: [], links: [] })
  /** 学科节点与其全部知识点构成的层级图 */
  const subjectGraph = ref<NeighborData>({ nodes: [], links: [] })
  /** 认知目标数据 */
  const cognitiveGoal = ref<CognitiveGoal | null>(null)
  /** 搜索结果 */
  const searchResults = ref<KnowledgeNode[]>([])
  /** 加载状态 */
  const loading = ref<boolean>(false)

  // ========== Misconception State ==========
  /** 当前节点的误解标注列表 */
  const misconceptions = ref<Misconception[]>([])
  /** "仅有误解标注"筛选开关 */
  const misconceptionFilter = ref<boolean>(false)

  // ========== 任务 State ==========
  /** 当前节点的关联任务 */
  const nodeTasks = ref<NodeTask[]>([])

  // ========== 跨学科 State ==========
  /** 跨学科图谱数据 */
  const crossSubjectData = ref<CrossSubjectResponse | null>(null)

  // ============ Actions ============

  /** 加载图谱广场统计 */
  async function loadSquareStats(): Promise<void> {
    loading.value = true
    try {
      squareStats.value = await graphApi.getSquareStats()
    } catch (error) {
      console.error('加载图谱广场失败:', error)
    } finally {
      loading.value = false
    }
  }

  /** 加载节点详情 */
  async function loadNodeDetail(nodeId: string): Promise<void> {
    loading.value = true
    try {
      currentGraph.value = await graphApi.getNodeDetail(nodeId)
    } catch (error) {
      console.error('加载节点详情失败:', error)
    } finally {
      loading.value = false
    }
  }

  /** 加载邻居节点 */
  async function loadNeighbors(nodeId: string, depth = 1, limit = 50): Promise<void> {
    loading.value = true
    try {
      neighborNodes.value = await graphApi.getNeighbors(nodeId, depth, limit)
    } catch (error) {
      console.error('加载邻居节点失败:', error)
    } finally {
      loading.value = false
    }
  }

  /** 加载学科与知识点的直接关联图 */
  async function loadSubjectGraph(subjectId: string): Promise<void> {
    loading.value = true
    try {
      subjectGraph.value = await graphApi.getSubjectGraph(subjectId)
    } catch (error) {
      console.error('加载学科层级图失败:', error)
      subjectGraph.value = { nodes: [], links: [] }
    } finally {
      loading.value = false
    }
  }

  /** 搜索知识节点 */
  async function searchNodes(q: string, subject?: string): Promise<void> {
    loading.value = true
    try {
      searchResults.value = await graphApi.searchNodes(q, subject)
    } catch (error) {
      console.error('搜索节点失败:', error)
    } finally {
      loading.value = false
    }
  }

  /** 加载认知目标 */
  async function loadCognitiveGoal(nodeId: string, includeAvg = false): Promise<void> {
    try {
      cognitiveGoal.value = await graphApi.getCognitiveGoals(nodeId, includeAvg)
    } catch (error) {
      console.error('加载认知目标失败:', error)
    }
  }

  // ========== Misconception Actions ==========

  /** 加载节点误解标注 */
  async function loadMisconceptions(nodeId: string): Promise<void> {
    try {
      misconceptions.value = await graphApi.getMisconceptions(nodeId)
    } catch (error) {
      console.error('加载误解标注失败:', error)
      misconceptions.value = []
    }
  }

  /** 添加误解标注 */
  async function addMisconception(nodeId: string, data: MisconceptionInput): Promise<void> {
    try {
      const mc = await graphApi.addMisconception(nodeId, data)
      misconceptions.value.push(mc)
      // 同步更新当前节点状态
      if (currentGraph.value && currentGraph.value.id === nodeId) {
        currentGraph.value.has_misconception = true
      }
    } catch (error) {
      console.error('添加误解标注失败:', error)
      throw error
    }
  }

  /** 更新误解标注 */
  async function updateMisconception(nodeId: string, mcId: string, data: Partial<MisconceptionInput>): Promise<void> {
    try {
      const updated = await graphApi.updateMisconception(nodeId, mcId, data)
      const idx = misconceptions.value.findIndex((m) => m.mc_id === mcId)
      if (idx !== -1) {
        misconceptions.value[idx] = updated
      }
    } catch (error) {
      console.error('更新误解标注失败:', error)
      throw error
    }
  }

  /** 删除误解标注 */
  async function deleteMisconception(nodeId: string, mcId: string): Promise<void> {
    try {
      await graphApi.deleteMisconception(nodeId, mcId)
      misconceptions.value = misconceptions.value.filter((m) => m.mc_id !== mcId)
      // 如果误解列表为空，更新节点状态
      if (misconceptions.value.length === 0 && currentGraph.value && currentGraph.value.id === nodeId) {
        currentGraph.value.has_misconception = false
      }
    } catch (error) {
      console.error('删除误解标注失败:', error)
      throw error
    }
  }

  /** AI辅助标注建议 */
  async function suggestMisconceptions(nodeId: string): Promise<MisconceptionSuggestion[]> {
    try {
      const response = await graphApi.suggestMisconceptions(nodeId)
      return response.suggestions
    } catch (error) {
      console.error('AI辅助标注建议失败:', error)
      return []
    }
  }

  // ========== 任务 Actions ==========

  /** 加载节点关联任务 */
  async function loadNodeTasks(nodeId: string): Promise<void> {
    try {
      nodeTasks.value = await graphApi.getNodeTasks(nodeId)
    } catch (error) {
      console.error('加载节点任务失败:', error)
      nodeTasks.value = []
    }
  }

  // ========== 跨学科 Actions ==========

  /** 加载跨学科关联图谱 */
  async function loadCrossSubject(subjects: string[], minStrength = 0.0, maxNodes = 100): Promise<void> {
    loading.value = true
    try {
      crossSubjectData.value = await graphApi.getCrossSubjectGraph(subjects, minStrength, maxNodes)
    } catch (error) {
      console.error('加载跨学科图谱失败:', error)
      crossSubjectData.value = null
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    squareStats,
    currentGraph,
    neighborNodes,
    subjectGraph,
    cognitiveGoal,
    searchResults,
    loading,
    misconceptions,
    misconceptionFilter,
    nodeTasks,
    crossSubjectData,
    // Actions
    loadSquareStats,
    loadNodeDetail,
    loadNeighbors,
    loadSubjectGraph,
    searchNodes,
    loadCognitiveGoal,
    loadMisconceptions,
    addMisconception,
    updateMisconception,
    deleteMisconception,
    suggestMisconceptions,
    loadNodeTasks,
    loadCrossSubject,
  }
})
