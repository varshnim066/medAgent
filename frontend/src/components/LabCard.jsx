import { FlaskConical } from 'lucide-react'

/**
 * Renders lab results grouped by section (CBC, LFT, KFT, etc.)
 */
export default function LabCard({ labs = {} }) {
  const sectionColors = {
    CBC:            'border-blue-500/30   text-blue-400',
    Inflammatory:   'border-red-500/30    text-red-400',
    LFT:            'border-amber-500/30  text-amber-400',
    KFT:            'border-purple-500/30 text-purple-400',
    Electrolytes:   'border-cyan-500/30   text-cyan-400',
    Glucose:        'border-orange-500/30 text-orange-400',
    Lipid_Profile:  'border-green-500/30  text-green-400',
    Urine_Analysis: 'border-slate-500/30  text-slate-300',
  }

  const formatValue = (val) => {
    if (val === null || val === undefined) return '—'
    if (typeof val === 'boolean') return val ? 'Yes' : 'No'
    return String(val)
  }

  return (
    <div className="space-y-4">
      {Object.entries(labs).map(([section, values]) => {
        const colorClass = sectionColors[section] || 'border-slate-500/30 text-slate-300'
        return (
          <div key={section} className={`card border ${colorClass.split(' ')[0]}`}>
            <div className={`flex items-center gap-2 px-4 py-2.5 border-b ${colorClass.split(' ')[0]}`}>
              <FlaskConical className={`w-4 h-4 ${colorClass.split(' ')[1]}`} />
              <h4 className={`text-sm font-semibold ${colorClass.split(' ')[1]}`}>
                {section.replace(/_/g, ' ')}
              </h4>
            </div>
            <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {typeof values === 'object' && !Array.isArray(values)
                ? Object.entries(values).map(([key, val]) => (
                    <div key={key} className="bg-slate-800/50 rounded-lg p-2.5">
                      <p className="text-xs text-slate-400 font-medium">{key.replace(/_/g, ' ')}</p>
                      <p className="text-sm font-semibold text-slate-100 mt-0.5 truncate">{formatValue(val)}</p>
                    </div>
                  ))
                : (
                  <div className="col-span-full">
                    <p className="text-sm text-slate-300">{formatValue(values)}</p>
                  </div>
                )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
