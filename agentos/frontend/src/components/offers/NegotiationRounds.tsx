// src/components/offers/NegotiationRounds.tsx
import React from 'react'
import type { OfferRound } from '../../api/types'
import { formatMinor } from '../../lib/money'
import { Badge } from '../ui/Badge'

interface NegotiationRoundsProps {
  rounds: OfferRound[]
  currency?: string
}

export const NegotiationRounds: React.FC<NegotiationRoundsProps> = ({ rounds, currency = 'USD' }) => {
  const sorted = [...rounds].sort((a, b) => a.round - b.round)

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-xs">
        <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
          <tr>
            <th className="px-3 py-2 text-left">Round</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-left">Listing / Scope</th>
            <th className="px-3 py-2 text-center">Packs &amp; Shipping</th>
            <th className="px-3 py-2 text-right">Line Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {sorted.map((r, idx) => {
            const isSelected = r.status === 'SELECTED'
            const packsText = r.packs && r.packs > 1 ? `${r.packs} packs` : '1 pack'
            const shippingText =
              r.shipping_minor !== undefined && r.shipping_minor > 0
                ? `+ ${formatMinor(r.shipping_minor, currency)} ship`
                : 'Free delivery'

            return (
              <tr
                key={`${r.round}-${idx}`}
                className={isSelected ? 'bg-emerald-50/60 font-medium' : 'hover:bg-slate-50'}
              >
                <td className="px-3 py-2 font-mono text-slate-600">
                  {r.round === 0 ? 'Offer (R0)' : `Comparison (R${r.round})`}
                </td>
                <td className="px-3 py-2">
                  <Badge
                    size="sm"
                    variant={
                      isSelected
                        ? 'emerald'
                        : r.status === 'ACCEPTED'
                        ? 'emerald'
                        : r.status === 'COUNTERED'
                        ? 'amber'
                        : r.status === 'OPEN'
                        ? 'blue'
                        : 'slate'
                    }
                  >
                    {r.status}
                  </Badge>
                </td>
                <td className="px-3 py-2 text-slate-700 max-w-xs truncate" title={r.scope}>
                  {r.scope || 'Standard store item'}
                </td>
                <td className="px-3 py-2 text-center font-mono text-slate-500 text-[11px]">
                  <span>{packsText}</span> &bull; <span className="text-slate-400">{shippingText}</span>
                </td>
                <td className="px-3 py-2 text-right font-mono font-semibold text-slate-900">
                  {formatMinor(r.price_minor, currency)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
