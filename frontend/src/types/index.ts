export interface GeneratePayload {
  student_class: string
  subject: string
  chapter: string
  medium: 'english' | 'hindi'
}

export interface GenerateResponse {
  job_id: string
  status: string
}

export interface JobStatus {
  job_id: string
  status: 'processing' | 'completed' | 'failed' | 'not_found'
  pdf_path: string | null
  error: string | null
  timing: Record<string, number> | null
  needs_review: boolean
}

export type GenerationState = 'idle' | 'generating' | 'completed' | 'failed'

export interface AgentStage {
  id: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  estimated_duration: number
}
