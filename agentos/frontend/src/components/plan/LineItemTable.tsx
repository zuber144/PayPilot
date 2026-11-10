// src/components/plan/LineItemTable.tsx
import React from 'react'
import type { PlanItem } from '../../api/types'
import { formatMinor } from '../../lib/money'

interface LineItemTableProps {
  items: PlanItem[]
  currency: string
}

export const LineItemTable: React.FC<LineItemTableProps> = ({ items, currency }) => {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-xs">
        <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
          <tr>
            <th className="px-4 py-3 text-left">Category / Need</th>
            <th className="px-4 py-3 text-left">Selected Provider</th>
            <th className="px-4 py-3 text-left">Agreed Scope</th>
            <th className="px-4 py-3 text-center">Timeline</th>
            <th className="px-4 py-3 text-right">Settlement Amount</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {items.map((item, idx) => (
            <tr key={`${item.provider_id}-${idx}`} className="hover:bg-slate-50 transition-colors">
              <td className="px-4 py-3 font-medium text-slate-900 uppercase font-mono text-[11px]">
                {item.need_key.replace('_', ' ')}
              </td>
              <td className="px-4 py-3 text-slate-800 font-semibold">{item.provider_name}</td>
              <td className="px-4 py-3 text-slate-600 max-w-xs">{item.scope}</td>
              <td className="px-4 py-3 text-center text-slate-600 font-mono">
                {item.timeline_days} days
              </td>
              <td className="px-4 py-3 text-right font-mono font-bold text-slate-900 text-sm">
                {formatMinor(item.price_minor, currency)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
