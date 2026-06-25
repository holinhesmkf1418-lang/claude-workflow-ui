<template>
  <div class="plan-viewer">
    <div v-if="displayContent" class="markdown-body" v-html="rendered"></div>
    <div v-else-if="loading" class="streaming-placeholder">
      <el-empty description="生成开发计划中…" />
    </div>
    <el-empty v-else description="暂无开发计划" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  plan: string | null
  loading?: boolean
  streamingContent?: string
}>()

const displayContent = computed(() => {
  return props.plan ?? props.streamingContent ?? null
})

const rendered = computed(() => {
  if (!displayContent.value) return ''
  return marked(displayContent.value, { breaks: true })
})
</script>

<style scoped>
.plan-viewer {
  padding: 8px 0;
  line-height: 1.8;
}
.streaming-placeholder {
  padding: 40px 0;
}
</style>
