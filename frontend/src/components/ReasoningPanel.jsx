import { Brain, List, Info, Search, Calendar, BookOpen, ChevronDown, ChevronUp } from 'lucide-react'
import ConfidenceBadge from './ConfidenceBadge'
import { useState } from 'react'

/**
 * Displays the full clinical reasoning output from the AI agent.
 */
export default function ReasoningPanel({ reasoning }) {
  const [showGuidelines, setShowGuidelines] = useState(false)

  if (!reasoning) return null

  const Section = ({ icon: Icon, title, items = [], color = 'blue' }) => {
    const colorMap = {
      blue:  'text-blue-400',
      amber: 'text-amber-400',
      red:   'text-red-400',
      green: 'text-emerald-400',
      purple:'text-purple-400',
    }
    return (
      <div className="card p-4">
        <div className={`flex items-center gap-2 mb-3 ${colorMap[color]}`}>
          <Icon className="w-4 h-4" />
          <h3 className="text-sm font-semibold">{title}</h3>
        </div>
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
              <span className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 bg-current ${colorMap[color]}`} />
              {item}
            </li>
          ))}
          {items.length === 0 && (
            <p className="text-sm text-slate-500 italic">None identified.</p>
          )}
        </ul>
      </div>
    )
  }

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-blue-400" />
          <h2 className="font-semibold text-slate-100">Clinical Reasoning</h2>
        </div>
        <ConfidenceBadge level={reasoning.confidence} score={reasoning.confidence_score} />
      </div>

      {/* Case Summary */}
      <div className="card p-4 border-blue-500/30 glow-blue">
        <div className="flex items-center gap-2 mb-2 text-blue-400">
          <Info className="w-4 h-4" />
          <h3 className="text-sm font-semibold">Case Summary</h3>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed">{reasoning.case_summary}</p>
      </div>

      {/* Sections Grid */}
      <div className="grid md:grid-cols-2 gap-4">
        <Section
          icon={List}
          title="Clinical Considerations"
          items={reasoning.considerations}
          color="blue"
        />
        <Section
          icon={Info}
          title="Missing Information"
          items={reasoning.missing_info}
          color="amber"
        />
        <Section
          icon={Search}
          title="Suggested Investigations"
          items={reasoning.investigations}
          color="purple"
        />
        <Section
          icon={Calendar}
          title="Follow-Up Recommendations"
          items={reasoning.follow_up}
          color="green"
        />
      </div>

      {/* Reasoning Trace */}
      {reasoning.reasoning_trace && (
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2 text-slate-400">
            <Brain className="w-4 h-4" />
            <h3 className="text-sm font-semibold text-slate-300">Reasoning Trace</h3>
          </div>
          <p className="text-sm text-slate-400 leading-relaxed font-mono bg-slate-800/50 rounded-lg p-3">
            {reasoning.reasoning_trace}
          </p>
        </div>
      )}

      {/* Retrieved Guidelines */}
      {reasoning.guidelines_used?.length > 0 && (
        <div className="card p-4">
          <button
            onClick={() => setShowGuidelines(v => !v)}
            className="w-full flex items-center justify-between"
          >
            <div className="flex items-center gap-2 text-slate-300">
              <BookOpen className="w-4 h-4 text-teal-400" />
              <h3 className="text-sm font-semibold">Retrieved Guidelines ({reasoning.guidelines_used.length})</h3>
            </div>
            {showGuidelines ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </button>
          {showGuidelines && (
            <div className="mt-3 space-y-2">
              {reasoning.guidelines_used.map((g, i) => (
                <div key={i} className="bg-slate-800/50 rounded-lg p-3 text-xs text-slate-400 leading-relaxed">
                  {g}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
