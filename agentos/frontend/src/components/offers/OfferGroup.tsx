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

const STORE_STYLES: Record<string, string> = {
  amazon: 'bg-amber-600 text-white',
  flipkart: 'bg-blue-600 text-white',
  meesho: 'bg-fuchsia-600 text-white',
}

const TAG_STYLES: Record<string, { label: string; cls: string }> = {
  BEST_PRICE: { label: '🏆 Best Price', cls: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  FASTEST_DELIVERY: { label: '⚡ Fastest Delivery', cls: 'bg-blue-100 text-blue-800 border-blue-200' },
  TOP_RATED: { label: '⭐ Top Rated', cls: 'bg-purple-100 text-purple-800 border-purple-200' },
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
          Product: <span className="text-navy-600 font-mono">{needKey.replace('_', ' ')}</span>
        </h4>
        <span className="text-xs text-slate-500 font-mono">{offers.length} store listing(s) compared</span>
      </div>

      <div className="space-y-4">
        {offers.map((providerOffer) => {
          const storeKey = providerOffer.store?.toLowerCase() ?? ''
          const storeBadgeCls = STORE_STYLES[storeKey] || 'bg-slate-700 text-white'
          const nativePrice =
            providerOffer.original_price_minor && providerOffer.original_currency
              ? formatMinor(providerOffer.original_price_minor, providerOffer.original_currency)
              : null

          return (
            <div
              key={providerOffer.provider_id}
              className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 space-y-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  {providerOffer.store && (
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded shadow-xs ${storeBadgeCls}`}
                    >
                      {providerOffer.store}
                    </span>
                  )}
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
                    ★ {providerOffer.rating.toFixed(1)}
                    {providerOffer.review_count ? ` (${providerOffer.review_count.toLocaleString()})` : ''} &bull;{' '}
                    {providerOffer.timeline_days}d delivery
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {providerOffer.tags?.map((tag) => {
                    const tagMeta = TAG_STYLES[tag]
                    if (!tagMeta) return null
                    return (
                      <span
                        key={tag}
                        className={`text-[10px] font-bold px-2 py-0.5 rounded border ${tagMeta.cls}`}
                      >
                        {tagMeta.label}
                      </span>
                    )
                  })}
                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-slate-900 block">
                      {formatMinor(providerOffer.final_price_minor, currency)}
                    </span>
                    {nativePrice && (
                      <span className="text-[10px] font-mono text-slate-500 block">
                        ({nativePrice})
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {providerOffer.product_title && (
                <div className="text-xs text-slate-700 flex items-center gap-1.5 pt-1">
                  <span className="font-medium text-slate-900">{providerOffer.product_title}</span>
                  {providerOffer.pack_size && providerOffer.pack_size > 1 && (
                    <span className="text-[10px] text-slate-500 bg-slate-200 px-1.5 py-0.2 rounded font-mono">
                      Pack of {providerOffer.pack_size}
                    </span>
                  )}
                  {providerOffer.url && (
                    <a
                      href={providerOffer.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-paypal-600 hover:text-paypal-700 text-[10px] font-semibold underline inline-flex items-center gap-0.5 ml-1"
                    >
                      View on Store &rarr;
                    </a>
                  )}
                </div>
              )}

              <NegotiationRounds rounds={providerOffer.rounds} currency={currency} />
            </div>
          )
        })}
      </div>
    </Card>
  )
}
