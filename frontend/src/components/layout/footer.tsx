import { Cpu, Sparkles } from 'lucide-react'

export function Footer() {
  return (
    <footer className="border-t border-gray-100 bg-gray-50/50">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Cpu className="h-4 w-4" />
            <span>Powered by LangGraph multi-agent workflow</span>
            <Sparkles className="h-3.5 w-3.5" />
            <span>LangSmith</span>
          </div>
          <p className="text-xs text-gray-400">
            Built with Mistral, Gemini, Groq, NVIDIA NIM, and Llama
          </p>
        </div>
      </div>
    </footer>
  )
}
