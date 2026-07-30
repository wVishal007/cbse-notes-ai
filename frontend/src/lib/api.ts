import { GeneratePayload, GenerateResponse, JobStatus } from '../types'

const API_BASE = '/api'

export async function generateNotes(payload: GeneratePayload): Promise<GenerateResponse> {
  const res = await fetch(`${API_BASE}/generate-notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function pollStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/status/${jobId}`)
  if (!res.ok) {
    throw new Error(`Failed to poll status: HTTP ${res.status}`)
  }
  return res.json()
}

export function getDownloadUrl(jobId: string): string {
  return `${API_BASE}/download/${jobId}`
}
