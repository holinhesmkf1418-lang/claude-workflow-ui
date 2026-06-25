<template>
  <MarkdownRenderer
    :content="plan"
    :loading="loading"
    :loading-text="'生成开发计划中…'"
    :streaming-content="streamingContent"
  />
</template>

<script setup lang="ts">
import MarkdownRenderer from './MarkdownRenderer.vue'

defineProps<{
  plan: string | null
  loading?: boolean
  streamingContent?: string
}>()
</script>
