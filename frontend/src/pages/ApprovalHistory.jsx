import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ClipboardList, CheckCircle, ChevronDown, ChevronUp, User } from 'lucide-react'
import axios from 'axios'
import ConfidenceBadge from '../components/ConfidenceBadge'

const API = 'http://localhost:8000'

export default function ApprovalHistory() {
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    axios.get(`${API}/history`).then(res => setRecs(res.data.recommendations || []))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Approval History</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          {recs.length} approved recommendations saved by doctors
        </p>
      </div>

      {loading ? (
        <div className="text-slate-400 animate-pulse text-center py-20">Loading history...</div>
      ) : recs.length === 0 ? (
        <div className="card p-10 text-center">
          <ClipboardList className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No approved recommendations yet.</p>
          <p className="text-slate-500 text-xs mt-1">
            Go to a patient visit, run reasoning, and approve a recommendation.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {recs.map(r => (
            <div key={r.rec_id} className="card overflow-hidden">
              {/* Row header */}
              <div
                onClick={() => setExpanded(expanded === r.rec_id ? null : r.rec_id)}
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/20 transition-colors"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className="w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={e => { e.stopPropagation(); navigate(`/patient/${r.patient_id}`) }}
                        className="font-medium text-slate-100 hover:text-blue-400 transition-colors text-sm"
                      >
                        {r.patient_name}
                      </button>
                      <span className="text-xs text-slate-500 font-mono">{r.visit_id}</span>
                    </div>
                    <p className="text-xs text-slate-400 truncate mt-0.5">
                      {r.case_summary?.slice(0, 90)}...
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                  <ConfidenceBadge level={r.confidence} score={r.confidence_score} />
                  <span className="text-xs text-slate-500 hidden md:inline">
                    {r.approved_at?.split('T')[0]}
                  </span>
                  {expanded === r.rec_id
                    ? <ChevronUp className="w-4 h-4 text-slate-400" />
                    : <ChevronDown className="w-4 h-4 text-slate-400" />
                  }
                </div>
              </div>

              {/* Expanded detail */}
              {expanded === r.rec_id && (
                <div className="border-t border-slate-700/60 p-4 space-y-4 animate-fade-in">
                  {/* Case summary */}
                  <div>
                    <p className="section-label">Case Summary</p>
                    <p className="text-sm text-slate-300 leading-relaxed">{r.case_summary}</p>
                  </div>

                  <div className="grid sm:grid-cols-2 gap-4">
                    {/* Considerations */}
                    <div>
                      <p className="section-label">Clinical Considerations</p>
                      <ul className="space-y-1">
                        {(r.considerations || []).map((c, i) => (
                          <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
                            <span className="mt-1.5 w-1 h-1 rounded-full bg-blue-400 flex-shrink-0" />
                            {c}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Investigations */}
                    <div>
                      <p className="section-label">Suggested Investigations</p>
                      <ul className="space-y-1">
                        {(r.investigations || []).map((inv, i) => (
                          <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
                            <span className="mt-1.5 w-1 h-1 rounded-full bg-purple-400 flex-shrink-0" />
                            {inv}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Critique */}
                  {r.critique_text && (
                    <div className="bg-slate-800/40 rounded-lg p-3">
                      <p className="section-label">Self-Critique</p>
                      <p className="text-xs text-slate-400 leading-relaxed">{r.critique_text}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
