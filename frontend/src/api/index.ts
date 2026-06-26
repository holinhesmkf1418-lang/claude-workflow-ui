import type { Project, ProjectListItem } from '@/types'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error (${res.status}): ${text}`)
  }
  return res.json()
}

export const api = {
  /** Create a new project and launch workflow */
  createProject(projectIdea: string, model?: string, githubRepo?: string, projectDir?: string): Promise<Project> {
    return request('/projects', {
      method: 'POST',
      body: JSON.stringify({
        project_idea: projectIdea,
        model: model || undefined,
        github_repo: githubRepo || undefined,
        project_dir: projectDir || undefined,
      }),
    })
  },

  /** List all projects */
  listProjects(): Promise<ProjectListItem[]> {
    return request('/projects')
  },

  /** Get project detail */
  getProject(id: string): Promise<Project> {
    return request(`/projects/${id}`)
  },

  /** Get SSE stream URL for a project */
  streamUrl(id: string): string {
    return `${BASE}/projects/${id}/stream`
  },

  /** Generate test instruction (测试生成) */
  testGenerate(scenario: string, projectId?: string, withAudit?: boolean, withDesign?: boolean): Promise<{
    instruction: string
  }> {
    return request('/test-generate', {
      method: 'POST',
      body: JSON.stringify({
        scenario,
        project_id: projectId || undefined,
        with_audit: withAudit || false,
        with_design: withDesign || false,
      }),
    })
  },

  /** Unified tool: audit / design */
  toolGenerate(tool: string, input: string, projectId?: string, techStack?: string): Promise<{ instruction: string }> {
    return request('/tool-generate', {
      method: 'POST',
      body: JSON.stringify({
        tool,
        input,
        project_id: projectId || undefined,
        tech_stack: techStack || undefined,
      }),
    })
  },

  /** Submit answers to PM's soul-searching questions and resume workflow */
  answerQuestions(projectId: string, answers: Record<string, string>): Promise<{ ok: boolean }> {
    return request(`/projects/${projectId}/answer`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    })
  },

  /** Delete a project */
  deleteProject(projectId: string): Promise<{ ok: boolean }> {
    return request(`/projects/${projectId}`, { method: 'DELETE' })
  },

  /** Analyze error log (BUG 调试) */
  debugAnalyze(errorLog: string, codeContext?: string, projectId?: string): Promise<{
    state: string
    root_cause: string
    risk: string
    machine_instruction: string
    explanation: string
    raw: string
  }> {
    return request('/debug', {
      method: 'POST',
      body: JSON.stringify({
        error_log: errorLog,
        code_context: codeContext || undefined,
        project_id: projectId || undefined,
      }),
    })
  },
}
