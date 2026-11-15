/**
 * 智慧学伴 资源管理 Store
 * 管理资源列表、当前资源、上传进度
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { resourceApi } from '@/services/resource'
import type { ResourceItem, ResourceDetail } from '@/services/resource'

export const useResourceStore = defineStore('resource', () => {
  // ============ State ============

  const resources = ref<ResourceItem[]>([])
  const currentResource = ref<ResourceDetail | null>(null)
  const uploadProgress = ref<number>(0)
  const total = ref<number>(0)
  const loading = ref<boolean>(false)

  // ============ Actions ============

  /** 加载资源列表 */
  async function loadResources(params?: {
    page?: number
    page_size?: number
    resource_type?: string
    search?: string
  }): Promise<void> {
    loading.value = true
    try {
      const response = await resourceApi.listResources(params)
      resources.value = response.items
      total.value = response.total
    } catch (error) {
      console.error('加载资源列表失败:', error)
    } finally {
      loading.value = false
    }
  }

  /** 上传文件 */
  async function uploadFile(
    file: File,
    options?: {
      title?: string
      description?: string
      resource_type?: string
      course_id?: number
    },
  ): Promise<unknown> {
    uploadProgress.value = 0
    try {
      const result = await resourceApi.uploadFile(file, options, (percent) => {
        uploadProgress.value = percent
      })
      return result
    } catch (error) {
      console.error('上传文件失败:', error)
      throw error
    }
  }

  /** 加载资源详情 */
  async function loadResourceDetail(resourceId: number): Promise<void> {
    loading.value = true
    try {
      currentResource.value = await resourceApi.getResourceDetail(resourceId)
    } catch (error) {
      console.error('加载资源详情失败:', error)
    } finally {
      loading.value = false
    }
  }

  /** 删除资源 */
  async function deleteResource(resourceId: number): Promise<void> {
    try {
      await resourceApi.deleteResource(resourceId)
      resources.value = resources.value.filter((r) => r.id !== resourceId)
    } catch (error) {
      console.error('删除资源失败:', error)
      throw error
    }
  }

  /** 关联知识点 */
  async function linkToNode(resourceId: number, nodeId: string): Promise<void> {
    try {
      await resourceApi.linkToNode(resourceId, nodeId)
    } catch (error) {
      console.error('关联知识点失败:', error)
      throw error
    }
  }

  return {
    resources,
    currentResource,
    uploadProgress,
    total,
    loading,
    loadResources,
    uploadFile,
    loadResourceDetail,
    deleteResource,
    linkToNode,
  }
})
