// src/components/goal/ProviderPanel.tsx
import React, { useState } from 'react'
import type { Provider } from '../../api/types'
import { formatMinor } from '../../lib/money'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'

interface ProviderPanelProps {
  providers: Provider[]
  isLoading?: boolean
}

const STORE_STYLES: Record<string, string> = {
  amazon: 'bg-amber-600 text-white',
  flipkart: 'bg-blue-600 text-white',
  meesho: 'bg-fuchsia-600 text-white',
}

export const ProviderPanel: React.FC<ProviderPanelProps> = ({ providers, isLoading }) => {
  const [filterCategory, setFilterCategory] = useState<string>('all')

  const categories = ['all', ...Array.from(new Set(providers.map((p) => p.category)))]

  const filtered = filterCategory === 'all'
    ? providers
    : providers.filter((p) => p.category === filterCategory)

  return (
    <Card padding="md" className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-semibold text-slate-900 text-base">Store &amp; Seller Marketplace</h3>
          <p className="text-xs text-slate-500">Autonomous agents search and compare prices across these listings</p>
        </div>
        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
          Catalog &amp; Live
        </span>
      </div>

      {/* Category filter pills */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setFilterCategory(cat)}
            className={`text-xs px-2.5 py-1 rounded-full transition-colors ${
              filterCategory === cat
                ? 'bg-navy-600 text-white font-medium'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {cat === 'all' ? 'All' : cat.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Provider list */}
      <div className="space-y-3 overflow-y-auto max-h-[500px] pr-1 flex-1">
        {isLoading && (
          <div className="text-xs text-slate-400 py-6 text-center">Loading marketplace listings…</div>
        )}
        {!isLoading && filtered.length === 0 && (
          <div className="text-xs text-slate-400 py-6 text-center">No listings found</div>
        )}
        {filtered.map((p) => {
          const storeKey = p.store?.toLowerCase() ?? ''
          const storeBadgeCls = STORE_STYLES[storeKey] || 'bg-slate-700 text-white'
          const nativePrice =
            p.original_price_minor && p.original_currency
              ? formatMinor(p.original_price_minor, p.original_currency)
              : null

          return (
            <div
              key={p.id}
              className="p-3 rounded-lg border border-slate-200 hover:border-slate-300 transition-colors bg-white text-xs space-y-1.5"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 truncate">
                  {p.store && (
                    <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${storeBadgeCls}`}>
                      {p.store}
                    </span>
                  )}
                  <span className="font-semibold text-slate-900 truncate">{p.name}</span>
                </div>
                {p.verified ? (
                  <Badge variant="emerald" size="sm">
                    Verified ✓
                  </Badge>
                ) : (
                  <Badge variant="red" size="sm">
                    Unverified ✗
                  </Badge>
                )}
              </div>

              <p className="text-slate-600 text-[11px] line-clamp-1 font-medium">
                {p.product_title || p.persona}
              </p>

              <div className="flex items-center justify-between text-slate-600 pt-1 border-t border-slate-100 text-[11px]">
                <div className="flex items-center gap-1">
                  <span className="font-mono font-bold text-slate-900">
                    {formatMinor(p.base_price_minor, 'USD')}
                  </span>
                  {nativePrice && (
                    <span className="font-mono text-slate-400 text-[10px]">
                      ({nativePrice})
                    </span>
                  )}
                </div>
                <span>★ {p.rating.toFixed(1)} {p.review_count ? `(${p.review_count})` : ''}</span>
                <span>{p.turnaround_days}d delivery</span>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
