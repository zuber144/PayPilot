// src/components/payguard/RiskGauge.tsx
import React from 'react'

interface RiskGaugeProps {
  score?: number | null // 0.0 - 1.0 float; or null/undefined if offline
  aiOk?: boolean
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({ score, aiOk = true }) => {
  if (score === null || score === undefined || !aiOk) {
    return (
      <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-center">
        <span className="text-xs text-slate-500 font-medium">
          ML Risk Engine Unavailable — Safe Default Applied
        </span>
      </div>
    )
  }

  // Normalize float 0.0-1.0 to percentage 0-100
  const normalizedScore = Math.min(1, Math.max(0, score))
  const percentage = Math.round(normalizedScore * 100)

  let levelText = 'Low Risk'
  let levelColor = 'text-emerald-700'
  let barColor = 'bg-emerald-500'

  if (normalizedScore >= 0.7) {
    levelText = 'High Risk (Block)'
    levelColor = 'text-red-700'
    barColor = 'bg-red-600'
  } else if (normalizedScore >= 0.4) {
    levelText = 'Medium Risk (Review)'
    levelColor = 'text-amber-700'
    barColor = 'bg-amber-500'
  }

  return (
    <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            PayGuard ML Risk Score
          </span>
          <div className="text-xl font-black font-mono text-slate-900 mt-0.5">
            {normalizedScore.toFixed(2)}{' '}
            <span className={`text-xs font-semibold ${levelColor}`}>({levelText})</span>
          </div>
        </div>
        <div className="text-right text-[11px] text-slate-400">
          <div>Thresholds:</div>
          <div>Review &ge; 0.40 | Block &ge; 0.70</div>
        </div>
      </div>

      {/* Progress track with threshold markers */}
      <div className="relative pt-2">
        <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden flex">
          <div
            style={{ width: `${percentage}%` }}
            className={`h-full transition-all duration-500 rounded-full ${barColor}`}
          />
        </div>

        {/* 0.40 marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-amber-400 pointer-events-none"
          style={{ left: '40%' }}
          title="Review Threshold (0.40)"
        />
        {/* 0.70 marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-red-400 pointer-events-none"
          style={{ left: '70%' }}
          title="Block Threshold (0.70)"
        />
      </div>

      <div className="flex justify-between text-[10px] text-slate-400 font-mono">
        <span>0.00 (Safe)</span>
        <span>0.40 (Review)</span>
        <span>0.70 (Block)</span>
        <span>1.00 (Critical)</span>
      </div>
    </div>
  )
}
