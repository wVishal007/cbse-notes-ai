import { Toaster } from 'react-hot-toast'
import { Layout } from './components/layout/layout'
import { HeroSection } from './components/HeroSection'
import { NotesForm } from './components/NotesForm'
import { ProgressTracker } from './components/ProgressTracker'
import { NotesPreview } from './components/NotesPreview'
import { ResultCard } from './components/ResultCard'
import { useSSEGeneration } from './hooks/useSSEGeneration'
import { AlertCircle, RefreshCw, ArrowLeft } from 'lucide-react'
import { Button } from './components/ui/button'
import { Card } from './components/ui/card'

export default function App() {
  const { state, content, agents, result, jobId, startGeneration, reset } = useSSEGeneration()

  const isGenerating = state === 'generating'
  const isCompleted = state === 'completed'
  const isFailed = state === 'failed'

  return (
    <Layout>
      <Toaster
        position="top-center"
        toastOptions={{
          duration: 4000,
          style: {
            borderRadius: '12px',
            padding: '12px 16px',
            fontSize: '14px',
            fontWeight: 500,
          },
          success: {
            iconTheme: { primary: '#059669', secondary: '#fff' },
          },
          error: {
            iconTheme: { primary: '#dc2626', secondary: '#fff' },
          },
        }}
      />

      {state === 'idle' && (
        <>
          <HeroSection />
          <div className="max-w-xl mx-auto">
            <NotesForm onSubmit={startGeneration} disabled={isGenerating} />
          </div>
        </>
      )}

      {(isGenerating || isCompleted || isFailed) && (
        <div className="max-w-2xl mx-auto space-y-4 px-0">
          <button
            onClick={reset}
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>

          <ProgressTracker agents={agents} />

          <NotesPreview content={content} isGenerating={isGenerating} />

          {isCompleted && result && jobId && (
            <ResultCard
              jobId={jobId}
              needsReview={result.needsReview}
              timing={result.timing}
              onReset={reset}
            />
          )}

          {isFailed && (
            <Card padding="lg" className="border-2 border-error">
              <div className="flex flex-col items-center text-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-error-light">
                  <AlertCircle className="h-6 w-6 text-error" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Generation Failed</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    Something went wrong. Check your API keys and try again.
                  </p>
                </div>
                <Button variant="primary" onClick={reset}>
                  <RefreshCw className="h-4 w-4" />
                  Try Again
                </Button>
              </div>
            </Card>
          )}
        </div>
      )}
    </Layout>
  )
}
