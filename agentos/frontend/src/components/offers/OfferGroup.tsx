// src/components/offers/OfferGroup.tsx
import React from 'react'
import type { ProviderOffers } from '../../api/types'
import { Card } from '../ui/Card'
import { NegotiationRounds } from './NegotiationRounds'
import { formatMinor } from '../../lib/money'
import { Badge } from '../ui/Badge'

interface OfferGroupProps {
  needKey: string
  offers: ProviderOffers[]
  currency?: string
}

export const OfferGroup: React.FC<OfferGroupProps> = ({
  needKey,
  offers = [],
  currency = 'USD',
}) => {
  return (
    <Card padding="md" className="space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
        <h4 className="font-bold text-sm text-slate-900 uppercase tracking-wide">
          Need: <span className="text-navy-600 font-mono">{needKey.replace('_', ' ')}</span>
        </h4>
        <span className="text-xs text-slate-500 font-mono">{offers.length} provider(s) bidding</span>
      </div>

      <div className="space-y-4">
        {offers.map((providerOffer) => {
          const savings =
            providerOffer.opening_price_minor > providerOffer.final_price_minor
              ? providerOffer.opening_price_minor - providerOffer.final_price_minor
              : 0

          return (
            <div
              key={providerOffer.provider_id}
              className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 space-y-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-xs text-slate-900">
                    {providerOffer.provider_name}
                  </span>
                  {providerOffer.verified ? (
                    <Badge variant="emerald" size="sm">
                      Verified ✓
                    </Badge>
                  ) : (
                    <Badge variant="red" size="sm">
                      Unverified ✗
                    </Badge>
                  )}
                  <span className="text-[11px] text-slate-500">
                    ★ {providerOffer.rating.toFixed(1)} &bull; {providerOffer.timeline_days}d delivery
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {savings > 0 && (
                    <span className="text-xs font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                      Saved {formatMinor(savings, currency)}
                    </span>
                  )}
                  <span className="text-xs font-mono font-bold text-slate-900">
                    Final: {formatMinor(providerOffer.final_price_minor, currency)}
                  </span>
                </div>
              </div>

              <NegotiationRounds rounds={providerOffer.rounds} currency={currency} />
            </div>
          )
        })}
      </div>
    </Card>
  )
}
