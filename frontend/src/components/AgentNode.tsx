import { CheckCircle2, Circle, Loader2, AlertCircle, Brain, Search, GitMerge, FileText, ShieldCheck, FileSpreadsheet, HelpingHand, Download } from 'lucide-react'
import { AgentStage } from '../types'

const AGENT_ICONS: Record<string, React.ReactNode> = {
  planner: <Brain className="h-5 w-5" />,
  research: <Search className="h-5 w-5" />,
  aggregator: <GitMerge className="h-5 w-5" />,
  synthesizer: <FileText className="h-5 w-5" />,
  validator: <ShieldCheck className="h-5 w-5" />,
  formatter: <FileSpreadsheet className="h-5 w-5" />,
  pyq_agent: <HelpingHand className="h-5 w-5" />,
  pdf_exporter: <Download className="h-5 w-5" />,
}

const STATUS_STYLES: Record<string, { icon: React.ReactNode; container: string; iconColor: string }> = {
  pending: {
    icon: <Circle className="h-5 w-5" />,
    container: 'border-gray-200 bg-gray-50',
    iconColor: 'text-gray-300',
  },
  running: {
    icon: <Loader2 className="h-5 w-5 animate-spin" />,
    container: 'border-primary bg-primary-light/30',
    iconColor: 'text-primary animate-agent-pulse',
  },
  completed: {
    icon: <CheckCircle2 className="h-5 w-5" />,
    container: 'border-success bg-success-light/30',
    iconColor: 'text-success',
  },
  failed: {
    icon: <AlertCircle className="h-5 w-5" />,
    container: 'border-error bg-error-light/30',
    iconColor: 'text-error',
  },
}

interface AgentNodeProps {
  agent: AgentStage
}

export function AgentNode({ agent }: AgentNodeProps) {
  const style = STATUS_STYLES[agent.status]
  const icon = AGENT_ICONS[agent.id]

  return (
    <div
      className={`flex items-center gap-4 rounded-xl border-2 p-4 transition-all duration-500 ${style.container} animate-scale-in`}
    >
      <div className={`flex-shrink-0 ${style.iconColor}`}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 truncate">{agent.label}</p>
        <p className="text-xs text-gray-500 capitalize">{agent.status}</p>
      </div>
      <div className={`flex-shrink-0 ${style.iconColor}`}>
        {style.icon}
      </div>
    </div>
  )
}
