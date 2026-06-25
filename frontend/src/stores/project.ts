import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { Project } from '@/types'
import { api } from '@/api'

export const useProjectStore = defineStore('project', () => {
  const currentProject = ref<Project | null>(null)
  const isStreaming = ref(false)

  /**
   * In-memory buffer for streaming content per step.
   * While a step is being generated, tokens accumulate here.
   * Once the step completes and the DB update arrives, the
   * viewer falls back to currentProject[step] instead.
   */
  const streamingContent = reactive<Record<string, string>>({
    prd: '',
    architecture: '',
    plan: '',
  })

  /**
   * Tracks which step is actively receiving stream tokens.
   */
  const activeStep = ref<string | null>(null)

  /**
   * PM's soul-searching questions for the user to answer.
   * Populated on `awaiting_input` SSE event or when `update`
   * delivers a project with `pending_questions` set.
   */
  const pendingQuestions = ref<string[]>([])

  /**
   * True while the frontend is submitting answers.
   */
  const submittingAnswers = ref(false)

  let eventSource: EventSource | null = null

  /**
   * Extract questions from project data.
   * Handles both SSE events and reconnection data.
   */
  function setQuestionsFromProject(p: Project) {
    if (p.pending_questions && p.status === 'awaiting_input') {
      try {
        const qs = JSON.parse(p.pending_questions)
        if (Array.isArray(qs) && qs.length > 0) {
          pendingQuestions.value = qs
          return
        }
      } catch { /* ignore */ }
    }
  }

  function connectSSE(projectId: string) {
    disconnectSSE()
    isStreaming.value = true
    // Reset streaming buffers on new connection
    streamingContent.prd = ''
    streamingContent.architecture = ''
    streamingContent.plan = ''
    activeStep.value = null
    pendingQuestions.value = []

    eventSource = new EventSource(api.streamUrl(projectId))

    eventSource.addEventListener('update', (e) => {
      try {
        const p: Project = JSON.parse(e.data)
        currentProject.value = p
        // Check if there are pending questions (for reconnections)
        setQuestionsFromProject(p)
        // Safety: if the project is no longer awaiting input, clear questions
        if (p.status !== 'awaiting_input' && pendingQuestions.value.length > 0) {
          pendingQuestions.value = []
        }
      } catch { /* ignore parse errors */ }
    })

    eventSource.addEventListener('token', (e) => {
      try {
        const data = JSON.parse(e.data)
        const { step, content } = data
        if (step && content && streamingContent[step] !== undefined) {
          streamingContent[step] += content
        }
      } catch { /* ignore */ }
    })

    eventSource.addEventListener('step_start', (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.step) {
          activeStep.value = data.step
          // Clear the buffer for this new step
          if (streamingContent[data.step] !== undefined) {
            streamingContent[data.step] = ''
          }
        }
      } catch { /* ignore */ }
    })

    eventSource.addEventListener('step_end', (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.step) {
          // Keep streaming content in buffer until the next update event
          // clears it (the DB now has the authoritative content)
          if (activeStep.value === data.step) {
            activeStep.value = null
          }
        }
      } catch { /* ignore */ }
    })

    eventSource.addEventListener('step_error', (e) => {
      try {
        const data = JSON.parse(e.data)
        console.error(`Workflow step '${data.step}' failed:`, data.error)
      } catch { /* ignore */ }
      activeStep.value = null
    })

    eventSource.addEventListener('awaiting_input', (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.questions && Array.isArray(data.questions)) {
          pendingQuestions.value = data.questions
        }
      } catch { /* ignore */ }
    })

    eventSource.addEventListener('completed', (e) => {
      try {
        currentProject.value = JSON.parse(e.data)
      } catch { /* ignore */ }
      isStreaming.value = false
      activeStep.value = null
      pendingQuestions.value = []
      disconnectSSE()
    })

    eventSource.addEventListener('failed', (e) => {
      try {
        currentProject.value = JSON.parse(e.data)
      } catch { /* ignore */ }
      isStreaming.value = false
      activeStep.value = null
      pendingQuestions.value = []
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

  /**
   * Submit answers to the PM's questions and resume the workflow.
   */
  async function submitAnswers(answers: Record<string, string>) {
    if (!currentProject.value) return
    submittingAnswers.value = true
    try {
      await api.answerQuestions(currentProject.value.id, answers)
      pendingQuestions.value = []
    } finally {
      submittingAnswers.value = false
    }
  }

  async function createAndWatch(projectIdea: string, model?: string, githubRepo?: string) {
    const project = await api.createProject(projectIdea, model, githubRepo)
    currentProject.value = project
    connectSSE(project.id)
    return project
  }

  function $reset() {
    disconnectSSE()
    currentProject.value = null
    streamingContent.prd = ''
    streamingContent.architecture = ''
    streamingContent.plan = ''
    activeStep.value = null
    pendingQuestions.value = []
  }

  return {
    currentProject,
    isStreaming,
    streamingContent,
    activeStep,
    pendingQuestions,
    submittingAnswers,
    connectSSE,
    disconnectSSE,
    createAndWatch,
    submitAnswers,
    $reset,
  }
})
