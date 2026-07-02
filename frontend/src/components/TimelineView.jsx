import { Calendar, FileText, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'

/**
 * Patient visit timeline — displays all visits chronologically.
 * Clicking a visit navigates to the reasoning page.
 */
export default function TimelineView({ visits = [], patientId, currentVisitId }) {
  const navigate = useNavigate()

  if (visits.length === 0) {
    return (
      <div className="text-center text-slate-500 py-10">
        No visits recorded.
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-4 top-0 bottom-0 w-px bg-slate-700/60" />

      <div className="space-y-4">
        {visits.map((visit, idx) => {
          const isCurrent = visit.visit_id === currentVisitId
          return (
            <div
              key={visit.visit_id}
              className={clsx(
                'relative pl-12 animate-fade-in',
                { 'animation-delay': idx * 50 }
              )}
            >
              {/* Circle on timeline */}
              <div className={clsx(
                'absolute left-2 top-3 w-5 h-5 rounded-full border-2 flex items-center justify-center',
                isCurrent
                  ? 'bg-blue-500 border-blue-400'
                  : 'bg-slate-700 border-slate-500'
              )}>
                <div className={clsx(
                  'w-2 h-2 rounded-full',
                  isCurrent ? 'bg-white' : 'bg-slate-400'
                )} />
              </div>

              {/* Card */}
              <div
                onClick={() => navigate(`/reason/${patientId}/${visit.visit_id}`)}
                className={clsx(
                  'card-hover p-4 cursor-pointer',
                  isCurrent && 'border-blue-500/40 glow-blue'
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                      <span className="text-xs text-slate-400">{visit.visit_date || visit.date}</span>
                      {isCurrent && (
                        <span className="badge bg-blue-500/20 text-blue-400 border border-blue-500/30">
                          Current
                        </span>
                      )}
                    </div>
                    <p className="font-medium text-slate-100 text-sm truncate">
                      {visit.chief_complaint}
                    </p>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                      {visit.doctor_assessment}
                    </p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {(visit.symptoms || []).slice(0, 3).map((s, i) => (
                        <span key={i} className="badge bg-slate-700/60 text-slate-300 text-[10px]">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0 mt-1" />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
