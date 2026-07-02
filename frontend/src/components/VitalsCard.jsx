import { Heart, Thermometer, Wind, Droplets, Ruler, Weight, Activity } from 'lucide-react'

/**
 * Displays patient vitals in a grid of visual cards.
 */
export default function VitalsCard({ vitals = {} }) {
  // Safe extraction of nested vitals
  const bp = vitals.blood_pressure || {}
  const systolic = bp.systolic || null
  const diastolic = bp.diastolic || null
  
  const formattedBP = systolic && diastolic ? `${systolic}/${diastolic} mmHg` : '—'
  const formattedPulse = vitals.pulse ? `${vitals.pulse} bpm` : '—'
  const formattedTemp = vitals.temperature ? `${vitals.temperature} °F` : '—'
  const formattedRR = vitals.respiratory_rate ? `${vitals.respiratory_rate} /min` : '—'
  const formattedSpo2 = vitals.spo2 ? `${vitals.spo2}%` : '—'
  const formattedHeight = vitals.height ? `${vitals.height} cm` : '—'
  const formattedWeight = vitals.weight ? `${vitals.weight} kg` : '—'
  const formattedBMI = vitals.bmi ? `${vitals.bmi} kg/m²` : '—'

  const items = [
    { key: 'bp', label: 'Blood Pressure', icon: Activity,    val: formattedBP,     color: 'text-rose-400', bg: 'bg-rose-500/10' },
    { key: 'hr', label: 'Pulse Rate',     icon: Heart,       val: formattedPulse,  color: 'text-pink-400', bg: 'bg-pink-500/10' },
    { key: 'tp', label: 'Temperature',    icon: Thermometer, val: formattedTemp,   color: 'text-amber-400', bg: 'bg-amber-500/10' },
    { key: 'rr', label: 'Resp. Rate',     icon: Wind,        val: formattedRR,     color: 'text-sky-400', bg: 'bg-sky-500/10' },
    { key: 'ox', label: 'SpO₂',           icon: Droplets,    val: formattedSpo2,   color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
    { key: 'ht', label: 'Height',         icon: Ruler,       val: formattedHeight, color: 'text-violet-400', bg: 'bg-violet-500/10' },
    { key: 'wt', label: 'Weight',         icon: Weight,      val: formattedWeight, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { key: 'bm', label: 'BMI',            icon: Weight,      val: formattedBMI,    color: 'text-orange-400', bg: 'bg-orange-500/10' },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {items.map(({ key, label, icon: Icon, color, bg, val }) => (
        <div key={key} className={`relative overflow-hidden card p-4 text-center transform transition-all hover:scale-105 hover:shadow-[0_0_20px_rgba(255,255,255,0.05)] border-t border-l border-white/5`}>
          <div className="absolute inset-0 opacity-20 bg-gradient-to-br from-white/10 to-transparent pointer-events-none" />
          <div className={`mx-auto w-10 h-10 flex items-center justify-center rounded-full mb-2 ${bg} ${color}`}>
            <Icon className="w-5 h-5" />
          </div>
          <p className="text-xs text-slate-400 font-medium tracking-wide uppercase">{label}</p>
          <p className="text-lg font-bold text-slate-100 mt-1">
            {val}
          </p>
        </div>
      ))}
    </div>
  )
}
