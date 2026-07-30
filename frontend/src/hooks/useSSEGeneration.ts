import { useState, useRef, useCallback, useEffect } from 'react'
import toast from 'react-hot-toast'
import { generateNotes } from '../lib/api'
import { AgentStage, GeneratePayload, GenerationState } from '../types'

const INITIAL_AGENTS: AgentStage[] = [
  { id: 'planner', label: 'Planner', status: 'pending', estimated_duration: 3 },
  { id: 'research', label: 'Research', status: 'pending', estimated_duration: 15 },
  { id: 'aggregator', label: 'Aggregator', status: 'pending', estimated_duration: 5 },
  { id: 'synthesizer', label: 'Synthesizer', status: 'pending', estimated_duration: 10 },
  { id: 'validator', label: 'Validator', status: 'pending', estimated_duration: 5 },
  { id: 'formatter', label: 'Formatter', status: 'pending', estimated_duration: 5 },
  { id: 'pyq_agent', label: 'PYQ Agent', status: 'pending', estimated_duration: 5 },
  { id: 'pdf_exporter', label: 'PDF Exporter', status: 'pending', estimated_duration: 3 },
]

interface SSEEvent {
  type: string
  node?: string
  content?: string
  pdf_path?: string | null
  timing?: Record<string, number> | null
  needs_review?: boolean
  message?: string
}

interface GenerateResult {
  pdf_path: string | null
  timing: Record<string, number> | null
  needsReview: boolean
}

export function useSSEGeneration() {
  const [state, setState] = useState<GenerationState>('idle')
  const [content, setContent] = useState('')
  const [agents, setAgents] = useState<AgentStage[]>(INITIAL_AGENTS)
  const [result, setResult] = useState<GenerateResult | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  const setAgentStatus = useCallback((nodeId: string, status: AgentStage['status']) => {
    setAgents((prev) =>
      prev.map((a) => (a.id === nodeId ? { ...a, status } : a))
    )
  }, [])

  const handleEvent = useCallback((data: SSEEvent) => {
    if (data.type === 'node_complete' && data.node) {
      setAgentStatus(data.node, 'completed')
      if (data.content) {
        setContent((prev) => {
          const separator = prev ? '\n\n---\n\n' : ''
          return prev + separator + data.content
        })
      }
    }

    if (data.type === 'complete') {
      setResult({
        pdf_path: data.pdf_path ?? null,
        timing: data.timing ?? null,
        needsReview: data.needs_review ?? false,
      })
      setState('completed')
      setAgents((prev) => prev.map((a) => ({ ...a, status: 'completed' as const })))
      toast.success('Notes generated successfully!')
    }

    if (data.type === 'error') {
      setState('failed')
      toast.error(data.message || 'Generation failed')
    }
  }, [setAgentStatus])

  const startGeneration = useCallback(
    async (payload: GeneratePayload) => {
      cleanup()
      setState('generating')
      setContent('')
      setAgents(INITIAL_AGENTS.map((a) => ({ ...a, status: 'pending' as const })))
      setResult(null)

      try {
        const { job_id } = await generateNotes(payload)
        setJobId(job_id)

        const es = new EventSource(`/api/stream/${job_id}`)
        eventSourceRef.current = es

        es.onmessage = (event) => {
          try {
            const data: SSEEvent = JSON.parse(event.data)
            handleEvent(data)
            if (data.type === 'complete' || data.type === 'error') {
              es.close()
              eventSourceRef.current = null
            }
          } catch {
            // ignore parse errors
          }
        }

        es.onerror = () => {
          es.close()
          eventSourceRef.current = null
          startPollFallback(job_id)
        }
      } catch (err: unknown) {
        setState('failed')
        toast.error(err instanceof Error ? err.message : 'Failed to start generation')
      }
    },
    [cleanup, handleEvent]
  )

  const startPollFallback = useCallback(
    (jobId: string) => {
      const timer = setInterval(async () => {
        try {
          const res = await fetch(`/api/status/${jobId}`)
          const status = await res.json()
          if (status.status === 'completed') {
            clearInterval(timer)
            pollIntervalRef.current = null
            setResult({
              pdf_path: status.pdf_path,
              timing: status.timing,
              needsReview: status.needs_review ?? false,
            })
            setState('completed')
            setAgents((prev) => prev.map((a) => ({ ...a, status: 'completed' as const })))
            toast.success('Notes generated successfully!')
          } else if (status.status === 'failed') {
            clearInterval(timer)
            pollIntervalRef.current = null
            setState('failed')
            toast.error(status.error || 'Generation failed')
          }
        } catch {
          // poll error, retry
        }
      }, 2000)
      pollIntervalRef.current = timer
    },
    []
  )

  const reset = useCallback(() => {
    cleanup()
    setState('idle')
    setContent('')
    setAgents(INITIAL_AGENTS)
    setResult(null)
    setJobId(null)
  }, [cleanup])

  useEffect(() => {
    return () => cleanup()
  }, [cleanup])

  return {
    state,
    content,
    agents,
    result,
    jobId,
    startGeneration,
    reset,
  }
}
