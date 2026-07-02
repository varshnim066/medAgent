import { NavLink } from 'react-router-dom'
import { Activity, Users, LayoutDashboard, ClipboardList, Stethoscope } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/',         label: 'Dashboard',  icon: LayoutDashboard },
  { to: '/patients', label: 'Patients',   icon: Users },
  { to: '/history',  label: 'History',    icon: ClipboardList },
]

export default function Navbar() {
  return (
    <header className="bg-[#1e293b] border-b border-slate-700/60 sticky top-0 z-50">
      <div className="max-w-screen-2xl mx-auto px-4 md:px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center group-hover:bg-blue-500 transition-colors">
            <Stethoscope className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="font-bold text-white text-sm leading-none">MedAgents</span>
            <p className="text-[10px] text-slate-400 leading-none mt-0.5">Clinical Decision Support</p>
          </div>
        </NavLink>

        {/* Nav Links */}
        <nav className="flex items-center gap-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
                )
              }
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Status indicator */}
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse-slow" />
          <span className="hidden md:inline">System Active</span>
        </div>
      </div>
    </header>
  )
}
