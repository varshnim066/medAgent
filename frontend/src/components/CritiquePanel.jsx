import { ShieldAlert, AlertTriangle, CheckCircle, XCircle, AlignLeft } from 'lucide-react'
import clsx from 'clsx'

/**
 * Displays the self-critique analysis of clinical reasoning.
 */
export default function CritiquePanel({ critique }) {
  if (!critique) return null

  const scorePercent = Math.round((critique.critique_score || 0.5) * 100)
  const scoreColor =
    scorePercent >= 70 ? 'text-emerald-400' :
    scorePercent >= 40 ? 'text-amber-400' : 'text-red-400'

  const FlagList = ({ title, items = [], icon: Icon, color }) => {
    const colorMap = {
      red:    'text-red-400 bg-red-500/10 border-red-500/20',
      amber:  'text-amber-400 bg-amber-500/10 border-amber-500/20',
      green:  'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
      slate:  'text-slate-400 bg-slate-700/40 border-slate-600/30',
    }
    const cls = colorMap[color] || colorMap.slate

    return (
      <div className={`rounded-xl border p-4 ${cls}`}>
        <div className={`flex items-center gap-2 mb-2 ${cls.split(' ')[0]}`}>
          <Icon className="w-4 h-4" />
          <h4 className="text-sm font-semibold">{title}</h4>
        </div>
        <ul className="space-y-1.5">
          {items.map((item, i) => (
            <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
              <span className="mt-1.5 w-1 h-1 rounded-full bg-current flex-shrink-0" />
              {item}
            </li>
          ))}
          {items.length === 0 && <li className="text-xs text-slate-500 italic">None identified</li>}
        </ul>
      </div>
    )
  }

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-400" />
          <h2 className="font-semibold text-slate-100">Self-Critique Analysis</h2>
        </div>
        <div className={clsx('text-sm font-bold', scoreColor)}>
          Quality Score: {scorePercent}%
        </div>
      </div>

      {/* Critique text */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-2 text-slate-300">
          <AlignLeft className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-semibold">Critique Summary</h3>
        </div>
        <p className="text-sm text-slate-400 leading-relaxed">{critique.critique_text}</p>
      </div>

      {/* Evidence + Guideline row */}
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="card p-4">
          <p className="text-xs text-slate-400 font-medium mb-1">Evidence Assessment</p>
          <p className="text-sm text-slate-200">{critique.evidence_assessment || '—'}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-slate-400 font-medium mb-1">Guideline Alignment</p>
          <p className="text-sm text-slate-200">{critique.guideline_alignment || '—'}</p>
        </div>
      </div>

      {/* Flags grid */}
      <div className="grid md:grid-cols-3 gap-4">
        <FlagList
          title="Missing Info Flags"
          items={critique.missing_info_flags}
          icon={AlertTriangle}
          color="amber"
        />
        <FlagList
          title="Hallucination Flags"
          items={critique.hallucination_flags}
          icon={XCircle}
          color="red"
        />
        <FlagList
          title="Contradiction Flags"
          items={critique.contradiction_flags}
          icon={CheckCircle}
          color="slate"
        />
      </div>

      {/* Revised reasoning */}
      {critique.revised_reasoning && (
        <div className="card p-4 border-blue-500/20">
          <div className="flex items-center gap-2 mb-2 text-blue-400">
            <CheckCircle className="w-4 h-4" />
            <h3 className="text-sm font-semibold">Revised Reasoning Suggestion</h3>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed bg-slate-800/50 rounded-lg p-3">
            {critique.revised_reasoning}
          </p>
        </div>
      )}
    </div>
  )
}
