// src/components/plan/PlanSummary.tsx
import React from 'react'
import type { Plan } from '../../api/types'
import { formatMinor } from '../../lib/money'
import { PLAN_STATUS_COLOR, PLAN_STATUS_LABEL } from '../../lib/constants'

interface PlanSummaryProps {
  plan: Plan
}

export const PlanSummary: React.FC<PlanSummaryProps> = ({ plan }) => {
  const maxDays = Math.max(...plan.items.map((i) => i.timeline_days), 0)

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
      <div>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Plan Status
        </span>
        <div className="mt-1">
          <span
            className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
              PLAN_STATUS_COLOR[plan.status] || 'bg-slate-100 text-slate-700'
            }`}
          >
            {PLAN_STATUS_LABEL[plan.status] || plan.status}
          </span>
        </div>
      </div>

      <div>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Total Amount
        </span>
        <div className="mt-1 font-mono font-bold text-slate-900 text-base">
          {formatMinor(plan.total_minor, plan.currency)}
        </div>
      </div>

      <div>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Deliverables
        </span>
        <div className="mt-1 font-semibold text-slate-800 text-sm">
          {plan.items.length} item(s)
        </div>
      </div>

      <div>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Est. Turnaround
        </span>
        <div className="mt-1 font-semibold text-slate-800 text-sm">
          {maxDays} days max
        </div>
      </div>
    </div>
  )
}
