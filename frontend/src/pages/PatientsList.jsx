import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Users, ChevronRight } from 'lucide-react'
import axios from 'axios'

const API = 'http://localhost:8000'

export default function PatientsList() {
  const [patients, setPatients] = useState([])
  const [filtered, setFiltered] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    axios.get(`${API}/patients`).then(res => {
      setPatients(res.data.patients || [])
      setFiltered(res.data.patients || [])
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const q = search.toLowerCase()
    setFiltered(patients.filter(p =>
      p.name?.toLowerCase().includes(q) ||
      p.patient_id?.toLowerCase().includes(q) ||
      p.past_medical?.join(' ').toLowerCase().includes(q)
    ))
  }, [search, patients])

  const genderBadge = (g) => g === 'Male'
    ? 'bg-blue-500/15 text-blue-400 border border-blue-500/20'
    : 'bg-pink-500/15 text-pink-400 border border-pink-500/20'

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Patients</h1>
          <p className="text-slate-400 text-sm">{patients.length} patients in the system</p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by name or ID..."
            className="input pl-9 w-64 text-sm"
          />
        </div>
      </div>

      {loading ? (
        <div className="text-slate-400 animate-pulse text-center py-20">Loading patients...</div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/60">
                {['Patient ID', 'Name', 'Age', 'Gender', 'Blood Group', 'Visits', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/40">
              {filtered.map(p => (
                <tr
                  key={p.patient_id}
                  onClick={() => navigate(`/patient/${p.patient_id}`)}
                  className="hover:bg-slate-700/30 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">{p.patient_id}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-blue-600/20 border border-blue-500/20 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-bold text-blue-400">
                          {p.name?.split(' ').map(n => n[0]).join('').slice(0,2)}
                        </span>
                      </div>
                      <span className="font-medium text-slate-100">{p.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{p.age}y</td>
                  <td className="px-4 py-3">
                    <span className={`badge text-xs ${genderBadge(p.gender)}`}>{p.gender}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{p.blood_group || '—'}</td>
                  <td className="px-4 py-3">
                    <span className="badge bg-slate-700/60 text-slate-300">{p.visit_count} visits</span>
                  </td>
                  <td className="px-4 py-3">
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center text-slate-500 py-12">
                    No patients found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
