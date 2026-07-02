import { useState } from 'react'
import { CheckCircle, XCircle, X } from 'lucide-react'
import axios from 'axios'

const API = 'http://localhost:8000'

/**
 * Doctor approval/rejection modal overlay.
 * On approve: saves recommendation to database.
 * On reject: logs decision only.
 */
export default function ApprovalModal({ reasoning, critique, onClose, onDecision }) {
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleDecision = async (decision) => {
    setLoading(true)
    try {
      const payload = {
        patient_id: reasoning.patient_id,
        visit_id:   reasoning.visit_id,
        decision,
        notes,
        case_summary:     decision === 'approved' ? reasoning.case_summary   : undefined,
        considerations:   decision === 'approved' ? reasoning.considerations : undefined,
        missing_info:     decision === 'approved' ? reasoning.missing_info   : undefined,
        investigations:   decision === 'approved' ? reasoning.investigations : undefined,
        follow_up:        decision === 'approved' ? reasoning.follow_up      : undefined,
        confidence:       decision === 'approved' ? reasoning.confidence     : undefined,
        confidence_score: decision === 'approved' ? reasoning.confidence_score : undefined,
        reasoning_trace:  decision === 'approved' ? reasoning.reasoning_trace : undefined,
        critique_text:    decision === 'approved' ? critique?.critique_text  : undefined,
        guidelines_used:  decision === 'approved' ? reasoning.guidelines_used : undefined,
      }

      const { data } = await axios.post(`${API}/approve`, payload)
      setResult({ success: true, decision, message: data.message })
      onDecision(decision)
    } catch (err) {
      setResult({ success: false, message: err.response?.data?.detail || 'Error occurred' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         style={{ background: 'rgba(0,0,0,0.75)' }}>
      <div className="card max-w-lg w-full p-6 animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-100">Doctor Review</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {!result ? (
          <>
            {/* Summary */}
            <div className="bg-slate-800/60 rounded-xl p-4 mb-4">
              <p className="text-xs text-slate-400 mb-1">Case Summary</p>
              <p className="text-sm text-slate-300 leading-relaxed line-clamp-4">
                {reasoning.case_summary}
              </p>
            </div>

            {/* Confidence */}
            <div className="flex items-center gap-3 mb-4">
              <span className="text-xs text-slate-400">Confidence:</span>
              <span className={`text-sm font-semibold ${
                reasoning.confidence === 'High' ? 'text-emerald-400' :
                reasoning.confidence === 'Medium' ? 'text-amber-400' : 'text-red-400'
              }`}>
                {reasoning.confidence} ({Math.round((reasoning.confidence_score || 0) * 100)}%)
              </span>
            </div>

            {/* Doctor notes */}
            <div className="mb-5">
              <label className="text-xs text-slate-400 block mb-1.5">
                Doctor Notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Add any notes about your decision..."
                rows={3}
                className="input text-sm resize-none"
              />
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => handleDecision('approved')}
                disabled={loading}
                className="btn-success flex-1 flex items-center justify-center gap-2"
              >
                <CheckCircle className="w-4 h-4" />
                {loading ? 'Processing...' : 'Approve & Save'}
              </button>
              <button
                onClick={() => handleDecision('rejected')}
                disabled={loading}
                className="btn-danger flex-1 flex items-center justify-center gap-2"
              >
                <XCircle className="w-4 h-4" />
                {loading ? 'Processing...' : 'Reject'}
              </button>
            </div>
          </>
        ) : (
          /* Result screen */
          <div className="text-center py-6">
            {result.success ? (
              <>
                <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 ${
                  result.decision === 'approved'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-red-500/20 text-red-400'
                }`}>
                  {result.decision === 'approved'
                    ? <CheckCircle className="w-8 h-8" />
                    : <XCircle className="w-8 h-8" />
                  }
                </div>
                <p className="text-slate-100 font-medium mb-1 capitalize">{result.decision}</p>
                <p className="text-sm text-slate-400">{result.message}</p>
              </>
            ) : (
              <p className="text-red-400">{result.message}</p>
            )}
            <button onClick={onClose} className="btn-ghost mt-5 w-full">Close</button>
          </div>
        )}
      </div>
    </div>
  )
}
