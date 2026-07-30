import { CheckCircle2, Circle, Loader2, AlertCircle } from 'lucide-react'
import { AgentStage } from '../types'

interface ProgressTrackerProps {
  agents: AgentStage[]
}

const STATUS_ICONS = {
  pending: Circle,
  running: Loader2,
  completed: CheckCircle2,
  failed: AlertCircle,
}

const STATUS_COLORS = {
  pending: 'border-gray-200 text-gray-300',
  running: 'border-primary text-primary',
  completed: 'border-success text-success',
  failed: 'border-error text-error',
}

const STATUS_BG = {
  pending: 'bg-gray-50',
  running: 'bg-primary/5',
  completed: 'bg-success/5',
  failed: 'bg-error/5',
}

export function ProgressTracker({ agents }: ProgressTrackerProps) {
  const completed = agents.filter((a) => a.status === 'completed').length
  const total = agents.length
  const progress = Math.round((completed / total) * 100)
  const activeIdx = agents.findIndex((a) => a.status === 'running')

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-gray-900">Multi-Agent Pipeline</span>
        <span className="text-gray-500">{completed}/{total}</span>
      </div>

      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-primary to-success rounded-full transition-all duration-700 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex flex-wrap gap-1.5">
        {agents.map((agent, i) => {
          const Icon = STATUS_ICONS[agent.status]
          const isActive = i === activeIdx
          return (
            <div
              key={agent.id}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs
                transition-all duration-500 ${STATUS_COLORS[agent.status]} ${STATUS_BG[agent.status]}
                ${isActive ? 'ring-2 ring-primary/20 scale-105' : ''}
                ${agent.status === 'pending' ? 'opacity-60' : 'opacity-100'}`}
            >
              <Icon className={`h-3 w-3 ${agent.status === 'running' ? 'animate-spin' : ''}`} />
              <span className="font-medium truncate max-w-[80px] sm:max-w-none">
                {agent.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
