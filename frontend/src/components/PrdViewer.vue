<template>
  <div class="prd-viewer">
    <div v-if="prd" class="markdown-body" v-html="rendered"></div>
    <el-empty v-else-if="loading" description="需求推演进行中…" />
    <el-empty v-else description="暂无 PRD 内容" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  prd: string | null
  loading?: boolean
}>()

const rendered = computed(() => {
  if (!props.prd) return ''
  return marked(props.prd, { breaks: true })
})
</script>

<style scoped>
.prd-viewer {
  padding: 8px 0;
  line-height: 1.8;
}
</style>
