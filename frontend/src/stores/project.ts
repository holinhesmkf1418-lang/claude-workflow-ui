import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Project } from '@/types'
import { api } from '@/api'

export const useProjectStore = defineStore('project', () => {
  const currentProject = ref<Project | null>(null)
  const isStreaming = ref(false)

  let eventSource: EventSource | null = null

  function connectSSE(projectId: string) {
    disconnectSSE()
    isStreaming.value = true
    eventSource = new EventSource(api.streamUrl(projectId))

    eventSource.addEventListener('update', (e) => {
      try {
        currentProject.value = JSON.parse(e.data)
      } catch { /* ignore parse errors */ }
    })

    eventSource.addEventListener('completed', (e) => {
      try {
        currentProject.value = JSON.parse(e.data)
      } catch { /* ignore */ }
      isStreaming.value = false
      disconnectSSE()
    })

    eventSource.addEventListener('failed', (e) => {
      try {
        currentProject.value = JSON.parse(e.data)
      } catch { /* ignore */ }
      isStreaming.value = false
      disconnectSSE()
    })

    eventSource.addEventListener('error', () => {
      // Will auto-reconnect; if repeatedly failing, stop
      if (eventSource?.readyState === EventSource.CLOSED) {
        isStreaming.value = false
        disconnectSSE()
      }
    })
  }

  function disconnectSSE() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    isStreaming.value = false
  }

  async function createAndWatch(projectIdea: string, model?: string) {
    const project = await api.createProject(projectIdea, model)
    currentProject.value = project
    connectSSE(project.id)
    return project
  }

  function $reset() {
    disconnectSSE()
    currentProject.value = null
  }

  return {
    currentProject,
    isStreaming,
    connectSSE,
    disconnectSSE,
    createAndWatch,
    $reset,
  }
})
