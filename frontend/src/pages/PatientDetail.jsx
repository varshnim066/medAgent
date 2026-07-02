import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Pill, AlertCircle, Stethoscope, Image } from 'lucide-react'
import axios from 'axios'
import TimelineView from '../components/TimelineView'
import VitalsCard from '../components/VitalsCard'
import LabCard from '../components/LabCard'

const API = 'http://localhost:8000'

const Tab = ({ label, active, onClick }) => (
  <button
    onClick={onClick}
    className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
      active
        ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
        : 'text-slate-400 hover:text-slate-200'
    }`}
  >
    {label}
  </button>
)

export default function PatientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [patient, setPatient] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('timeline')

  useEffect(() => {
    axios.get(`${API}/patient/${id}`).then(res => setPatient(res.data))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <div className="text-slate-400 animate-pulse text-center py-24">Loading patient...</div>
  }

  if (!patient) {
    return <div className="text-red-400 text-center py-24">Patient not found.</div>
  }

  const latest = patient.latest_visit || {}

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Back button */}
      <button
        onClick={() => navigate('/patients')}
        className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Patients
      </button>

      {/* Patient profile header */}
      <div className="card p-5">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          {/* Avatar */}
          <div className="w-16 h-16 rounded-2xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center flex-shrink-0">
            <User className="w-7 h-7 text-blue-400" />
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-white">{patient.name}</h1>
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-sm text-slate-400">
              <span>{patient.age} years</span>
              <span>•</span>
              <span>{patient.gender}</span>
              <span>•</span>
              <span>Blood Group: {patient.blood_group || '—'}</span>
              <span>•</span>
              <span className="font-mono text-xs">{patient.patient_id}</span>
            </div>
          </div>
          {/* CTA: Reason for latest visit */}
          {latest.visit_id && (
            <button
              onClick={() => navigate(`/reason/${id}/${latest.visit_id}`)}
              className="btn-primary flex items-center gap-2 flex-shrink-0"
            >
              <Stethoscope className="w-4 h-4" />
              Run Clinical Reasoning
            </button>
          )}
        </div>
      </div>

      {/* Quick info row */}
      <div className="grid sm:grid-cols-3 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2 text-red-400">
            <AlertCircle className="w-4 h-4" />
            <h3 className="text-xs font-semibold uppercase tracking-wider">Allergies</h3>
          </div>
          <div className="flex flex-wrap gap-1">
            {(patient.allergies || []).map((a, i) => (
              <span key={i} className="badge bg-red-500/10 text-red-400 border border-red-500/20 text-xs">{a}</span>
            ))}
          </div>
        </div>
        <div className="card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Past Medical History</h3>
          <div className="flex flex-wrap gap-1">
            {(patient.past_medical || []).map((m, i) => (
              <span key={i} className="badge bg-slate-700/60 text-slate-300 text-xs">{m}</span>
            ))}
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2 text-amber-400">
            <Pill className="w-4 h-4" />
            <h3 className="text-xs font-semibold uppercase tracking-wider">Current Medications</h3>
          </div>
          <div className="flex flex-wrap gap-1">
            {(latest.medications || []).map((m, i) => (
              <span key={i} className="badge bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs">{m}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap border-b border-slate-700/60 pb-3">
        {['timeline', 'vitals', 'labs', 'imaging', 'notes'].map(t => (
          <Tab key={t} label={t.charAt(0).toUpperCase() + t.slice(1)} active={tab === t} onClick={() => setTab(t)} />
        ))}
      </div>

      {/* Tab content */}
      {tab === 'timeline' && (
        <TimelineView visits={patient.visits || []} patientId={id} currentVisitId={latest.visit_id} />
      )}

      {tab === 'vitals' && (
        <div className="space-y-4">
          {(patient.visits || []).slice(-1).map(v => (
            <div key={v.visit_id}>
              <p className="text-xs text-slate-400 mb-3">Latest Visit — {v.visit_date}</p>
              <VitalsCard vitals={v.vitals || {}} />
            </div>
          ))}
        </div>
      )}

      {tab === 'labs' && (
        <div>
          {(patient.visits || []).slice(-1).map(v => (
            <div key={v.visit_id}>
              <p className="text-xs text-slate-400 mb-3">Latest Visit — {v.visit_date}</p>
              <LabCard labs={v.labs || {}} />
            </div>
          ))}
        </div>
      )}

      {tab === 'imaging' && (
        <div className="grid sm:grid-cols-2 gap-4">
          {Object.entries(latest.imaging || {}).map(([modality, data]) => (
            <div key={modality} className="card p-4">
              <div className="flex items-center gap-2 mb-2 text-teal-400">
                <Image className="w-4 h-4" />
                <h3 className="text-sm font-medium">{modality}</h3>
              </div>
              <p className="text-sm text-slate-300">{data?.finding || data?.impression || '—'}</p>
            </div>
          ))}
        </div>
      )}

      {tab === 'notes' && (
        <div className="space-y-4">
          {(patient.visits || []).map(v => (
            <div key={v.visit_id} className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-slate-400">{v.visit_date}</span>
                <span className="badge bg-slate-700/60 text-slate-300 text-[10px]">{v.icd10_code}</span>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">{v.clinical_notes}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
