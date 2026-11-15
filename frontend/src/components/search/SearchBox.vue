<template>
  <div class="search-box">
    <el-autocomplete
      ref="autocompleteRef"
      v-model="query"
      :fetch-suggestions="fetchSuggestions"
      placeholder="搜索资源、笔记、知识点..."
      :trigger-on-focus="false"
      clearable
      class="search-box__input"
      @select="handleSelect"
      @keyup.enter="handleSearch"
      @focus="handleFocus"
      @blur="handleBlur"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
      <template #suffix>
        <el-tag size="small" type="info" class="search-box__shortcut">Ctrl+K</el-tag>
      </template>
    </el-autocomplete>

    <!-- 搜索历史下拉 -->
    <div v-if="showHistory && searchStore.searchHistory.length > 0" class="search-box__history">
      <div class="search-box__history-header">
        <span>搜索历史</span>
        <el-button link type="danger" size="small" @click="searchStore.clearHistory()">清空</el-button>
      </div>
      <div
        v-for="item in searchStore.searchHistory"
        :key="item"
        class="search-box__history-item"
        @click="handleHistoryClick(item)"
      >
        <el-icon><Clock /></el-icon>
        <span>{{ item }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智慧学伴 全局搜索框
 * el-autocomplete + 搜索历史 + Ctrl+K 快捷键
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, Clock } from '@element-plus/icons-vue'
import { useSearchStore } from '@/stores/search'

const router = useRouter()
const route = useRoute()
const searchStore = useSearchStore()

const query = ref('')
const showHistory = ref(false)
const autocompleteRef = ref()

interface SuggestionItem {
  value: string
}

async function fetchSuggestions(qs: string, cb: (items: SuggestionItem[]) => void): Promise<void> {
  if (!qs.trim()) {
    cb([])
    return
  }
  try {
    await searchStore.getSuggestions(qs)
    const items = searchStore.suggestions.map((s) => ({ value: s }))
    cb(items)
  } catch {
    cb([])
  }
}

function handleSelect(item: SuggestionItem): void {
  if (item.value) {
    navigateToSearch(item.value)
  }
}

function handleSearch(): void {
  if (query.value.trim()) {
    navigateToSearch(query.value)
  }
}

function handleHistoryClick(item: string): void {
  query.value = item
  showHistory.value = false
  navigateToSearch(item)
}

function navigateToSearch(q: string): void {
  router.push({
    name: 'Search',
    params: { sceneType: route.params.sceneType || 'self-study' },
    query: { q },
  })
}

function handleFocus(): void {
  showHistory.value = true
}

function handleBlur(): void {
  setTimeout(() => {
    showHistory.value = false
  }, 200)
}

// Ctrl+K 快捷键
function handleKeydown(e: KeyboardEvent): void {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    if (autocompleteRef.value) {
      autocompleteRef.value.focus()
    }
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style lang="scss" scoped>
.search-box {
  position: relative;

  &__input {
    width: 280px;

    :deep(.el-input__wrapper) {
      border-radius: 20px;
    }
  }

  &__shortcut {
    font-size: 11px;
    padding: 0 4px;
  }

  &__history {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--color-bg-primary);
    border: 1px solid var(--color-border-light);
    border-radius: var(--border-radius-md);
    box-shadow: var(--shadow-md);
    z-index: 200;
    padding: 8px 0;
  }

  &__history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 12px;
    font-size: 13px;
    color: var(--color-text-secondary);
  }

  &__history-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 14px;
    color: var(--color-text-regular);

    &:hover {
      background: var(--color-bg-secondary);
    }
  }
}
</style>
