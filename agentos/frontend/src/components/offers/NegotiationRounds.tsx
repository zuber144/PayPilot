// src/components/offers/NegotiationRounds.tsx
import React from 'react'
import type { Offer } from '../../api/types'
import { formatMinor } from '../../lib/money'
import { Badge } from '../ui/Badge'

interface NegotiationRoundsProps {
  offers: Offer[]
  currency?: string
}

export const NegotiationRounds: React.FC<NegotiationRoundsProps> = ({ offers, currency = 'USD' }) => {
  const sorted = [...offers].sort((a, b) => a.round - b.round)

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-xs">
        <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
          <tr>
            <th className="px-3 py-2 text-left">Round</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-left">Offered Scope</th>
            <th className="px-3 py-2 text-right">Quote</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {sorted.map((offer) => {
            const isSelected = offer.status === 'SELECTED'
            return (
              <tr
                key={offer.id}
                className={isSelected ? 'bg-emerald-50/50 font-medium' : 'hover:bg-slate-50'}
              >
                <td className="px-3 py-2 font-mono text-slate-600">Round {offer.round}</td>
                <td className="px-3 py-2">
                  <Badge
                    size="sm"
                    variant={
                      isSelected
                        ? 'emerald'
                        : offer.status === 'OPEN'
                        ? 'blue'
                        : 'slate'
                    }
                  >
                    {offer.status}
                  </Badge>
                </td>
                <td className="px-3 py-2 text-slate-700">{offer.scope}</td>
                <td className="px-3 py-2 text-right font-mono font-semibold text-slate-900">
                  {formatMinor(offer.price_minor, currency)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
