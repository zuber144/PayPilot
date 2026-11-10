// src/components/offers/OfferGroup.tsx
import React from 'react'
import type { Offer, Provider } from '../../api/types'
import { Card } from '../ui/Card'
import { NegotiationRounds } from './NegotiationRounds'
import { formatMinor } from '../../lib/money'

interface OfferGroupProps {
  needKey: string
  offers: Offer[]
  providers?: Provider[]
  currency?: string
}

export const OfferGroup: React.FC<OfferGroupProps> = ({
  needKey,
  offers,
  providers = [],
  currency = 'USD',
}) => {
  // Group offers by provider_id
  const byProvider = offers.reduce<Record<number, Offer[]>>((acc, o) => {
    if (!acc[o.provider_id]) acc[o.provider_id] = []
    acc[o.provider_id].push(o)
    return acc
  }, {})

  const providerMap = new Map(providers.map((p) => [p.id, p]))

  return (
    <Card padding="md" className="space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
        <h4 className="font-bold text-sm text-slate-900 uppercase tracking-wide">
          Need: <span className="text-navy-600 font-mono">{needKey.replace('_', ' ')}</span>
        </h4>
        <span className="text-xs text-slate-500 font-mono">{offers.length} offer(s) logged</span>
      </div>

      <div className="space-y-4">
        {Object.entries(byProvider).map(([providerIdStr, providerOffers]) => {
          const providerId = Number(providerIdStr)
          const provider = providerMap.get(providerId)
          const selected = providerOffers.find((o) => o.status === 'SELECTED')
          const initial = providerOffers.find((o) => o.round === 1)
          const savings =
            initial && selected && initial.price_minor > selected.price_minor
              ? initial.price_minor - selected.price_minor
              : 0

          return (
            <div key={providerId} className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-xs text-slate-900">
                    {provider?.name ?? `Provider #${providerId}`}
                  </span>
                  {provider?.verified && (
                    <span className="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                      Verified
                    </span>
                  )}
                </div>
                {savings > 0 && (
                  <span className="text-xs font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                    Agent saved {formatMinor(savings, currency)}
                  </span>
                )}
              </div>

              <NegotiationRounds offers={providerOffers} currency={currency} />
            </div>
          )
        })}
      </div>
    </Card>
  )
}
