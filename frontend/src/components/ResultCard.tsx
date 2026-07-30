import { useState } from 'react'
import { Download, CheckCircle2, AlertTriangle, RefreshCw, Clock, ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from './ui/button'
import { getDownloadUrl } from '../lib/api'

interface ResultCardProps {
  jobId: string
  needsReview: boolean
  timing: Record<string, number> | null
  onReset: () => void
}

export function ResultCard({ jobId, needsReview, timing, onReset }: ResultCardProps) {
  const [showTiming, setShowTiming] = useState(false)
  const downloadUrl = getDownloadUrl(jobId)

  return (
    <div className="space-y-3">
      <div className={`rounded-xl border-2 p-4 text-center transition-all duration-500 animate-in slide-in-from-bottom-4
        ${needsReview ? 'border-warning bg-warning/5' : 'border-success bg-success/5'}`}
      >
        <div className="flex items-center justify-center gap-2 mb-2">
          {needsReview
            ? <AlertTriangle className="h-5 w-5 text-warning" />
            : <CheckCircle2 className="h-5 w-5 text-success" />
          }
          <h3 className="text-base font-bold text-gray-900">
            {needsReview ? 'Needs Review' : 'Ready'}
          </h3>
        </div>
        <p className="text-xs text-gray-500 mb-3">
          {needsReview
            ? 'Some sections may need human review'
            : 'Notes generated with practice questions'}
        </p>

        <div className="flex flex-col sm:flex-row gap-2 justify-center">
          <a
            href={downloadUrl}
            download
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary text-white px-5 py-2.5 text-sm font-semibold
              hover:bg-primary-dark transition-all duration-200 active:scale-[0.97]"
          >
            <Download className="h-4 w-4" />
            Download PDF
          </a>
          <Button variant="outline" onClick={onReset} size="sm">
            <RefreshCw className="h-4 w-4" />
            New
          </Button>
        </div>
      </div>

      {timing && Object.keys(timing).length > 0 && (
        <div className="border border-gray-100 rounded-xl overflow-hidden">
          <button
            onClick={() => setShowTiming(!showTiming)}
            className="flex w-full items-center justify-between px-4 py-2.5 text-left hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Clock className="h-3.5 w-3.5 text-gray-400" />
              <span className="text-xs font-medium text-gray-600">Timing</span>
            </div>
            {showTiming
              ? <ChevronUp className="h-3.5 w-3.5 text-gray-400" />
              : <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
            }
          </button>
          {showTiming && (
            <div className="px-4 pb-3 space-y-1 animate-in slide-in-from-top-1 duration-200">
              {Object.entries(timing).map(([node, seconds]) => (
                <div key={node} className="flex items-center justify-between text-xs">
                  <span className="text-gray-600 capitalize">{node.replace(/_/g, ' ')}</span>
                  <span className="font-mono text-gray-900 font-medium">{seconds.toFixed(1)}s</span>
                </div>
              ))}
              <div className="border-t border-gray-100 pt-1.5 mt-1.5 flex items-center justify-between text-xs font-semibold">
                <span className="text-gray-900">Total</span>
                <span className="font-mono text-primary">
                  {Object.values(timing).reduce((a, b) => a + b, 0).toFixed(1)}s
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
