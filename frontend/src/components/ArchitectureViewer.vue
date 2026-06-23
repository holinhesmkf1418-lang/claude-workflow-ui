<template>
  <div class="architecture-viewer">
    <div v-if="architecture" class="markdown-body" v-html="rendered"></div>
    <el-empty v-else-if="loading" description="架构设计进行中…" />
    <el-empty v-else description="暂无架构内容" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  architecture: string | null
  loading?: boolean
}>()

const rendered = computed(() => {
  if (!props.architecture) return ''
  return marked(props.architecture, { breaks: true })
})
</script>

<style scoped>
.architecture-viewer {
  padding: 8px 0;
  line-height: 1.8;
}
</style>
