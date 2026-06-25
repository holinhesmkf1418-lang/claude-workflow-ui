<template>
  <MarkdownRenderer
    :content="prd"
    :loading="loading"
    :loading-text="'需求推演进行中…'"
    :streaming-content="streamingContent"
  />
</template>

<script setup lang="ts">
import MarkdownRenderer from './MarkdownRenderer.vue'

defineProps<{
  prd: string | null
  loading?: boolean
  streamingContent?: string
}>()
</script>
