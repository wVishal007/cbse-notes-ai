import { useState } from 'react'
import { BookText, Languages, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Select } from './ui/select'
import { Card } from './ui/card'
import { GeneratePayload } from '../types'

const CLASS_OPTIONS = Array.from({ length: 12 }, (_, i) => ({
  value: String(i + 1),
  label: `Class ${i + 1}`,
}))

const MEDIUM_OPTIONS: { value: 'english' | 'hindi'; label: string }[] = [
  { value: 'english', label: 'English' },
  { value: 'hindi', label: 'Hindi (हिन्दी)' },
]

interface NotesFormProps {
  onSubmit: (payload: GeneratePayload) => void
  disabled: boolean
}

export function NotesForm({ onSubmit, disabled }: NotesFormProps) {
  const [studentClass, setStudentClass] = useState('10')
  const [subject, setSubject] = useState('')
  const [chapter, setChapter] = useState('')
  const [medium, setMedium] = useState<'english' | 'hindi'>('english')
  const [errors, setErrors] = useState<Record<string, string>>({})

  function validate(): boolean {
    const newErrors: Record<string, string> = {}
    if (!studentClass) newErrors.studentClass = 'Select a class'
    if (!subject.trim()) newErrors.subject = 'Subject is required'
    if (!chapter.trim()) newErrors.chapter = 'Chapter is required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return
    const payload: GeneratePayload = {
      student_class: studentClass,
      subject: subject.trim(),
      chapter: chapter.trim(),
      medium,
    }
    toast.success('Starting note generation...')
    onSubmit(payload)
  }

  return (
    <Card className="animate-slide-up" padding="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex items-center gap-2 text-gray-900 mb-1">
          <BookText className="h-5 w-5 text-primary flex-shrink-0" />
          <h3 className="text-lg font-semibold">Chapter Details</h3>
        </div>

        <Select
          label="Class"
          options={CLASS_OPTIONS}
          value={studentClass}
          onChange={(e) => setStudentClass(e.target.value)}
          error={errors.studentClass}
        />

        <Input
          label="Subject"
          placeholder="e.g. Science, Maths"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          error={errors.subject}
        />

        <Input
          label="Chapter Name"
          placeholder="e.g. Chemical Reactions and Equations"
          value={chapter}
          onChange={(e) => setChapter(e.target.value)}
          error={errors.chapter}
        />

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-gray-700">Medium</label>
          <div className="flex rounded-xl border-2 border-gray-200 overflow-hidden">
            {MEDIUM_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setMedium(opt.value)}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium transition-all duration-200 min-h-[44px]
                  ${medium === opt.value
                    ? 'bg-primary text-white shadow-sm'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
              >
                <Languages className="h-4 w-4 flex-shrink-0" />
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <Button type="submit" size="lg" loading={disabled} disabled={disabled} className="w-full min-h-[48px]">
          <Sparkles className="h-4 w-4" />
          {disabled ? 'Generating...' : 'Generate Notes'}
        </Button>
      </form>
    </Card>
  )
}
