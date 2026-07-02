import clsx from 'clsx'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

/**
 * Confidence badge — displays Low / Medium / High with appropriate color and icon.
 */
export default function ConfidenceBadge({ level, score }) {
  const config = {
    High:   { cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', label: 'High',   Icon: TrendingUp },
    Medium: { cls: 'bg-amber-500/15   text-amber-400   border-amber-500/30',   label: 'Medium', Icon: Minus },
    Low:    { cls: 'bg-red-500/15     text-red-400     border-red-500/30',     label: 'Low',    Icon: TrendingDown },
  }

  const cfg = config[level] || config.Low
  const Icon = cfg.Icon

  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border', cfg.cls)}>
      <Icon className="w-3 h-3" />
      {cfg.label} Confidence
      {score !== undefined && (
        <span className="ml-1 opacity-70">({Math.round(score * 100)}%)</span>
      )}
    </span>
  )
}
