import { Sparkles, BookOpen, Brain, FileText } from 'lucide-react'

export function HeroSection() {
  return (
    <div className="animate-slide-down text-center mb-10 sm:mb-14">
      <div className="inline-flex items-center gap-1.5 rounded-full bg-primary-light px-4 py-1.5 text-sm font-medium text-primary mb-4">
        <Sparkles className="h-4 w-4" />
        Multi-Agent AI Workflow
      </div>
      <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-gray-900 leading-tight tracking-tight">
        Generate NCERT-Aligned
        <br />
        <span className="text-primary">Study Notes</span>
      </h2>
      <p className="mt-4 text-base sm:text-lg text-gray-500 max-w-2xl mx-auto leading-relaxed">
        Enter your class, subject, and chapter — our multi-agent AI system researches, writes, validates, and formats
        CBSE study notes with practice questions.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-6 text-sm text-gray-400">
        <span className="flex items-center gap-1.5">
          <BookOpen className="h-4 w-4" />
          NCERT Curriculum
        </span>
        <span className="flex items-center gap-1.5">
          <Brain className="h-4 w-4" />
          8 Specialized Agents
        </span>
        <span className="flex items-center gap-1.5">
          <FileText className="h-4 w-4" />
          PDF with PYQs
        </span>
      </div>
    </div>
  )
}
