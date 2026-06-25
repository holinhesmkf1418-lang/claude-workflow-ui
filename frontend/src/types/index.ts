export interface TaskItem {
  id: number
  task_id: string
  title: string
  phase: string
  description: string | null
  goal: string
  requirements: string
  constraints: string | null
  acceptance: string
  codex_instruction: string
}

export interface Project {
  id: string
  project_idea: string
  model: string | null
  github_repo: string | null
  status: 'pending' | 'running' | 'awaiting_input' | 'completed' | 'failed'
  status_detail: string
  error: string | null
  pending_questions: string | null  // JSON array of questions
  user_answers: string | null       // JSON object
  prd: string | null
  architecture: string | null
  plan: string | null
  created_at: string
  updated_at: string
  tasks: TaskItem[]
}

export interface ProjectListItem {
  id: string
  project_idea: string
  status: string
  status_detail: string
  created_at: string
}
