// src/components/plan/BudgetBar.tsx
import React from 'react'
import { formatMinor } from '../../lib/money'

interface BudgetBarProps {
  totalMinor: number
  budgetMinor: number
  currency: string
}

export const BudgetBar: React.FC<BudgetBarProps> = ({ totalMinor, budgetMinor, currency }) => {
  const percent = budgetMinor > 0 ? Math.round((totalMinor / budgetMinor) * 100) : 0
  const isOver = totalMinor > budgetMinor
  const difference = Math.abs(budgetMinor - totalMinor)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-slate-700">Budget Utilization</span>
        <span className="font-mono text-slate-600">
          <strong>{formatMinor(totalMinor, currency)}</strong> of {formatMinor(budgetMinor, currency)} ({percent}%)
        </span>
      </div>

      {/* Progress track */}
      <div className="h-2.5 w-full bg-slate-200 rounded-full overflow-hidden flex">
        <div
          style={{ width: `${Math.min(100, percent)}%` }}
          className={`h-full transition-all duration-500 rounded-full ${
            isOver ? 'bg-red-500' : percent > 85 ? 'bg-amber-500' : 'bg-paypal-500'
          }`}
        />
      </div>

      <div className="flex justify-between items-center text-[11px] text-slate-500">
        <span>0%</span>
        <span>
          {isOver ? (
            <span className="text-red-600 font-semibold">
              Exceeds budget by {formatMinor(difference, currency)}
            </span>
          ) : (
            <span className="text-emerald-700 font-medium">
              {formatMinor(difference, currency)} remaining under cap
            </span>
          )}
        </span>
        <span>100% Cap</span>
      </div>
    </div>
  )
}
