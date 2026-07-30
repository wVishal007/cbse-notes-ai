import { useEffect, useRef } from 'react'
import { FileText } from 'lucide-react'
import { Card } from './ui/card'

interface NotesPreviewProps {
  content: string
  isGenerating: boolean
}

export function NotesPreview({ content, isGenerating }: NotesPreviewProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [content])

  if (!content && !isGenerating) return null

  return (
    <Card padding="md" className="border-primary/20">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-gray-900">
          {isGenerating ? 'Generating Notes...' : 'Generated Notes'}
        </h3>
        {isGenerating && (
          <span className="ml-auto flex items-center gap-1.5 text-xs text-primary">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
            Live
          </span>
        )}
      </div>

      <div
        ref={scrollRef}
        className="prose prose-sm max-w-none overflow-y-auto rounded-lg bg-gray-50 p-4 
          prose-headings:text-gray-900 prose-headings:font-bold
          prose-h1:text-lg prose-h2:text-base prose-h3:text-sm
          prose-strong:text-gray-900 prose-strong:font-semibold
          prose-ul:list-disc prose-ol:list-decimal
          prose-p:text-gray-700 prose-p:leading-relaxed
          prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded
          prose-blockquote:border-l-primary prose-blockquote:bg-gray-100/50
          [&>*]:animate-in [&>*]:fade-in [&>*]:slide-in-from-bottom-1 [&>*]:duration-300"
        style={{ maxHeight: 'min(70vh, 600px)' }}
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
      />
    </Card>
  )
}

function renderMarkdown(md: string): string {
  const html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')

  return `<p>${html}</p>`
}
