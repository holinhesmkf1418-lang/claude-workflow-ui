<template>
  <MarkdownRenderer
    :content="architecture"
    :loading="loading"
    :loading-text="'架构设计进行中…'"
    :streaming-content="streamingContent"
  />
</template>

<script setup lang="ts">
import MarkdownRenderer from './MarkdownRenderer.vue'

defineProps<{
  architecture: string | null
  loading?: boolean
  streamingContent?: string
}>()
</script>
