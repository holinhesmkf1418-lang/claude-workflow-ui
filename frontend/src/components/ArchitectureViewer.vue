<template>
  <div class="architecture-viewer">
    <div v-if="displayContent" class="markdown-body" v-html="rendered"></div>
    <div v-else-if="loading" class="streaming-placeholder">
      <el-empty description="架构设计进行中…" />
    </div>
    <el-empty v-else description="暂无架构内容" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  architecture: string | null
  loading?: boolean
  /** Optional streaming content — shown when db content is still null */
  streamingContent?: string
}>()

/**
 * Display the authoritative content from DB first,
 * fall back to in-memory streaming buffer while step is active.
 */
const displayContent = computed(() => {
  return props.architecture ?? props.streamingContent ?? null
})

const rendered = computed(() => {
  if (!displayContent.value) return ''
  return marked(displayContent.value, { breaks: true })
})
</script>

<style scoped>
.architecture-viewer {
  padding: 8px 0;
  line-height: 1.8;
}
.streaming-placeholder {
  padding: 40px 0;
}
</style>
