import { useEffect, useState } from 'react'
import { Users, Activity, CheckCircle, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import StatCard from '../components/StatCard'

const API = 'http://localhost:8000'

const CHART_COLORS = [
  '#3b82f6','#8b5cf6','#10b981','#f59e0b','#ef4444',
  '#06b6d4','#ec4899','#84cc16','#f97316','#6366f1',
  '#14b8a6','#a855f7','#fb923c','#22c55e','#e11d48',
]

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([
      axios.get(`${API}/dashboard/stats`),
      axios.get(`${API}/patients`),
    ]).then(([statsRes, patientsRes]) => {
      setStats(statsRes.data)
      setPatients(patientsRes.data.patients?.slice(0, 8) || [])
    }).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Clinical Dashboard</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          Agentic Decision Support — Human-in-the-Loop
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Patients"           value={stats?.total_patients}             icon={Users}        color="blue"   />
        <StatCard label="Total Visits"             value={stats?.total_visits}               icon={Activity}     color="purple" />
        <StatCard label="Approved Recommendations" value={stats?.approved_recommendations}   icon={CheckCircle}  color="green"  />
        <StatCard label="Pending Reviews"          value={stats?.pending_reviews}            icon={Clock}        color="amber"  />
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Disease distribution bar chart */}
        <div className="card p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Disease Distribution (Top 15)</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={stats?.disease_distribution || []}
              layout="vertical"
              margin={{ left: 8, right: 16, top: 4, bottom: 4 }}
            >
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis
                type="category"
                dataKey="disease"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                width={130}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: 'rgba(255,255,255,0.03)' }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {(stats?.disease_distribution || []).map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Age distribution pie chart */}
        <div className="card p-4">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Age Distribution</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={stats?.age_distribution || []}
                dataKey="count"
                nameKey="range"
                cx="50%"
                cy="50%"
                outerRadius={90}
                innerRadius={50}
                paddingAngle={3}
                label={({ range, percent }) => `${range} (${(percent * 100).toFixed(0)}%)`}
                labelLine={{ stroke: '#475569' }}
              >
                {(stats?.age_distribution || []).map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent patients */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300">Recent Patients</h2>
          <button
            onClick={() => navigate('/patients')}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            View All →
          </button>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {patients.map(p => (
            <div
              key={p.patient_id}
              onClick={() => navigate(`/patient/${p.patient_id}`)}
              className="card-hover p-3"
            >
              {/* Avatar */}
              <div className="w-8 h-8 rounded-full bg-blue-600/30 border border-blue-500/30 flex items-center justify-center mb-2">
                <span className="text-xs font-bold text-blue-400">
                  {p.name?.split(' ').map(n => n[0]).join('').slice(0,2)}
                </span>
              </div>
              <p className="text-sm font-medium text-slate-100 truncate">{p.name}</p>
              <p className="text-xs text-slate-400">{p.age}y • {p.gender}</p>
              <p className="text-xs text-slate-500 mt-1">{p.visit_count} visits</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
