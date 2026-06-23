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
  createProject(projectIdea: string, model?: string): Promise<Project> {
    return request('/projects', {
      method: 'POST',
      body: JSON.stringify({ project_idea: projectIdea, model: model || undefined }),
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
}
