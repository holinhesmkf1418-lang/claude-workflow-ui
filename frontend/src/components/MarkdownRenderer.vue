<template>
  <div class="markdown-renderer" ref="containerRef">
    <div v-if="content" class="markdown-body" v-html="rendered"></div>
    <div v-else-if="loading" class="loading-placeholder">
      <el-empty :description="loadingText" />
    </div>
    <el-empty v-else description="暂无内容" />

    <!-- Auto-scroll toggle (only visible when streaming) -->
    <div v-if="streamingContent && content === null" class="auto-scroll-bar">
      <el-button text size="small" @click="toggleAutoScroll">
        <span v-if="autoScroll">⏸ 自动滚动中</span>
        <span v-else>⬇ 恢复自动滚动</span>
      </el-button>
      <span class="streaming-status">实时接收中…</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { marked } from 'marked'

const props = defineProps<{
  content: string | null
  loading?: boolean
  loadingText?: string
  /** Streaming content to show while db content is still null */
  streamingContent?: string
}>()

const containerRef = ref<HTMLElement | null>(null)
const autoScroll = ref(true)

/**
 * Display authoritative content from DB first,
 * fall back to in-memory streaming buffer while step is active.
 */
const displayContent = computed(() => {
  return props.content ?? props.streamingContent ?? null
})

const rendered = computed(() => {
  if (!displayContent.value) return ''
  return marked(displayContent.value, { breaks: true })
})

// ─── Auto-scroll ───────────────────────────────────────────

function scrollToBottom() {
  if (!autoScroll.value) return
  nextTick(() => {
    const el = containerRef.value
    if (!el) return
    // Scroll the page so the bottom of this component is visible
    const rect = el.getBoundingClientRect()
    window.scrollTo({
      top: window.scrollY + rect.bottom - window.innerHeight + 24,
      behavior: 'smooth',
    })
  })
}

/** Disable auto-scroll when the user scrolls up manually */
function onWindowScroll() {
  if (!autoScroll.value) return
  // How far from the bottom of the page?
  const distanceFromBottom = document.documentElement.scrollHeight - window.scrollY - window.innerHeight
  if (distanceFromBottom > 120) {
    autoScroll.value = false
  }
}

function toggleAutoScroll() {
  if (autoScroll.value) {
    autoScroll.value = false
  } else {
    autoScroll.value = true
    scrollToBottom()
  }
}

// Watch streaming content length changes → scroll
watch(() => props.streamingContent?.length ?? 0, () => {
  scrollToBottom()
})

onMounted(() => {
  window.addEventListener('scroll', onWindowScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', onWindowScroll)
})

// ─── Mermaid rendering ─────────────────────────────────────

watch(rendered, async () => {
  await nextTick()
  if (!containerRef.value) return

  const codeBlocks = containerRef.value.querySelectorAll<HTMLElement>('pre code.language-mermaid')
  if (codeBlocks.length === 0) return

  const mermaidModule = await import('mermaid')
  const mermaid = mermaidModule.default
  mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
  })

  for (const codeEl of codeBlocks) {
    const pre = codeEl.closest('pre')
    if (!pre || pre.dataset.mermaidProcessed) continue
    pre.dataset.mermaidProcessed = 'true'

    const code = codeEl.textContent || ''
    const mermaidId = `mermaid-${Math.random().toString(36).slice(2, 8)}`

    const diagram = document.createElement('div')
    diagram.className = 'mermaid'
    diagram.id = mermaidId
    diagram.textContent = code

    pre.parentNode?.replaceChild(diagram, pre)
  }

  try {
    await mermaid.run({ querySelector: '.mermaid' })
  } catch (e) {
    console.warn('Mermaid render error:', e)
  }
}, { immediate: false })
</script>

<style scoped>
.markdown-renderer {
  padding: 8px 0;
  line-height: 1.8;
}
.loading-placeholder {
  padding: 40px 0;
}
.auto-scroll-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  margin-top: 8px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
  color: #909399;
}
.streaming-status {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
