import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Brain, ShieldAlert, CheckCircle, Loader2 } from 'lucide-react'
import axios from 'axios'
import ReasoningPanel from '../components/ReasoningPanel'
import CritiquePanel from '../components/CritiquePanel'
import ApprovalModal from '../components/ApprovalModal'
import VitalsCard from '../components/VitalsCard'
import LabCard from '../components/LabCard'

const API = 'http://localhost:8000'

export default function ReasoningPage() {
  const { patientId, visitId } = useParams()
  const navigate = useNavigate()

  const [patient, setPatient]       = useState(null)
  const [visit, setVisit]           = useState(null)
  const [reasoning, setReasoning]   = useState(null)
  const [critique, setCritique]     = useState(null)
  const [showModal, setShowModal]   = useState(false)
  const [approved, setApproved]     = useState(null)

  const [loadingPatient, setLoadingPatient]     = useState(true)
  const [loadingReasoning, setLoadingReasoning] = useState(false)
  const [loadingCritique, setLoadingCritique]   = useState(false)
  const [step, setStep] = useState('idle') // idle | reasoning | critique | done

  // Load patient and visit
  useEffect(() => {
    axios.get(`${API}/patient/${patientId}`).then(res => {
      setPatient(res.data)
      const found = (res.data.visits || []).find(v => v.visit_id === visitId)
      setVisit(found || res.data.latest_visit)
    }).finally(() => setLoadingPatient(false))
  }, [patientId, visitId])

  const runReasoning = async () => {
    setStep('reasoning')
    setLoadingReasoning(true)
    setReasoning(null)
    setCritique(null)
    setApproved(null)
    try {
      const { data } = await axios.post(`${API}/reason`, {
        patient_id: patientId,
        visit_id: visitId,
      })
      setReasoning(data)
      setStep('critique')
      // Auto-run critique
      await runCritique(data)
    } catch (err) {
      alert('Reasoning error: ' + (err.response?.data?.detail || err.message))
      setStep('idle')
    } finally {
      setLoadingReasoning(false)
    }
  }

  const runCritique = async (reasoningData) => {
    setLoadingCritique(true)
    try {
      const { data } = await axios.post(`${API}/critique`, {
        patient_id: patientId,
        visit_id: visitId,
        reasoning: reasoningData.reasoning_trace,
        case_summary: reasoningData.case_summary,
      })
      setCritique(data)
      setStep('done')
    } catch (err) {
      console.warn('Critique error:', err.message)
      setStep('done')
    } finally {
      setLoadingCritique(false)
    }
  }

  if (loadingPatient) {
    return <div className="text-slate-400 animate-pulse text-center py-24">Loading patient...</div>
  }

  return (
    <div className="space-y-5 animate-fade-in max-w-6xl">
      {/* Back */}
      <button
        onClick={() => navigate(`/patient/${patientId}`)}
        className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Patient
      </button>

      {/* Header */}
      <div className="card p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white">{patient?.name}</h1>
            <p className="text-sm text-slate-400 mt-0.5">
              {patient?.age}y • {patient?.gender} •{' '}
              <span className="font-mono text-xs">{visitId}</span>
            </p>
            {visit && (
              <p className="text-sm text-slate-300 mt-1">
                <span className="text-slate-400">Chief Complaint: </span>
                {visit.chief_complaint}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={runReasoning}
              disabled={loadingReasoning || loadingCritique}
              className="btn-primary flex items-center gap-2"
            >
              {(loadingReasoning || loadingCritique) ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Brain className="w-4 h-4" />
              )}
              {step === 'idle' ? 'Run Clinical Reasoning' :
               step === 'reasoning' ? 'Generating Reasoning...' :
               step === 'critique' ? 'Running Self-Critique...' : 'Re-Run'}
            </button>
            {step === 'done' && reasoning && (
              <button
                onClick={() => setShowModal(true)}
                className="btn-success flex items-center gap-2"
              >
                <CheckCircle className="w-4 h-4" />
                Doctor Review
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Approved/Rejected banner */}
      {approved && (
        <div className={`rounded-xl p-4 flex items-center gap-3 ${
          approved === 'approved'
            ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/30 text-red-400'
        }`}>
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm font-medium">
            Recommendation {approved === 'approved' ? 'approved and saved' : 'rejected'} successfully.
          </span>
        </div>
      )}

      {/* Main content grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left: Visit data */}
        <div className="space-y-4">
          {visit && (
            <>
              <div className="card p-4">
                <h2 className="text-sm font-semibold text-slate-300 mb-3">Vitals</h2>
                <VitalsCard vitals={visit.vitals || {}} />
              </div>
              <div className="card p-4">
                <h2 className="text-sm font-semibold text-slate-300 mb-3">Clinical Notes</h2>
                <p className="text-sm text-slate-400 leading-relaxed">{visit.clinical_notes}</p>
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-300 mb-3">Laboratory Results</h2>
                <LabCard labs={visit.labs || {}} />
              </div>
            </>
          )}
        </div>

        {/* Right: Reasoning + Critique */}
        <div className="space-y-6">
          {/* Idle state */}
          {step === 'idle' && (
            <div className="card p-10 text-center">
              <Brain className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 text-sm">Click "Run Clinical Reasoning" to start the agent pipeline.</p>
              <p className="text-slate-500 text-xs mt-1">
                The system will retrieve relevant history, guidelines, generate reasoning, and self-critique.
              </p>
            </div>
          )}

          {/* Loading */}
          {loadingReasoning && (
            <div className="card p-10 text-center">
              <Loader2 className="w-10 h-10 text-blue-400 animate-spin mx-auto mb-3" />
              <p className="text-slate-300 text-sm font-medium">Generating clinical reasoning...</p>
              <p className="text-slate-500 text-xs mt-1">Retrieving patient history and guidelines via FAISS → Gemini API</p>
            </div>
          )}

          {/* Reasoning panel */}
          {reasoning && <ReasoningPanel reasoning={reasoning} />}

          {/* Critique loading */}
          {loadingCritique && (
            <div className="card p-6 flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-amber-400 animate-spin flex-shrink-0" />
              <p className="text-sm text-slate-300">Running self-critique analysis...</p>
            </div>
          )}

          {/* Critique panel */}
          {critique && <CritiquePanel critique={critique} />}
        </div>
      </div>

      {/* Approval modal */}
      {showModal && reasoning && (
        <ApprovalModal
          reasoning={reasoning}
          critique={critique}
          onClose={() => setShowModal(false)}
          onDecision={(decision) => {
            setApproved(decision)
            setShowModal(false)
          }}
        />
      )}
    </div>
  )
}
