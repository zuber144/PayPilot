// src/components/plan/LineItemTable.tsx
import React from 'react'
import type { PlanItem } from '../../api/types'
import { formatMinor } from '../../lib/money'

interface LineItemTableProps {
  items: PlanItem[]
  currency: string
}

const STORE_STYLES: Record<string, string> = {
  amazon: 'bg-amber-600 text-white',
  flipkart: 'bg-blue-600 text-white',
  meesho: 'bg-fuchsia-600 text-white',
}

export const LineItemTable: React.FC<LineItemTableProps> = ({ items, currency }) => {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200 text-xs">
        <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
          <tr>
            <th className="px-4 py-3 text-left">Item / Category</th>
            <th className="px-4 py-3 text-left">Store &amp; Listing</th>
            <th className="px-4 py-3 text-center">Packs &amp; Delivery</th>
            <th className="px-4 py-3 text-right">Settlement Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {items.map((item, idx) => {
            const storeKey = item.store?.toLowerCase() ?? ''
            const storeBadgeCls = STORE_STYLES[storeKey] || 'bg-slate-700 text-white'
            const nativePrice =
              item.original_price_minor && item.original_currency
                ? formatMinor(item.original_price_minor, item.original_currency)
                : null

            return (
              <tr key={`${item.provider_id}-${idx}`} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 font-medium text-slate-900 uppercase font-mono text-[11px]">
                  {item.need_key.replace('_', ' ')}
                </td>
                <td className="px-4 py-3 space-y-1">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {item.store && (
                      <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${storeBadgeCls}`}>
                        {item.store}
                      </span>
                    )}
                    <span className="text-slate-800 font-semibold">{item.provider_name}</span>
                  </div>
                  {item.product_title && (
                    <div className="text-[11px] text-slate-600">
                      {item.url ? (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                          className="hover:underline text-slate-700 font-medium inline-flex items-center gap-1"
                        >
                          {item.product_title} &rarr;
                        </a>
                      ) : (
                        item.product_title
                      )}
                    </div>
                  )}
                  {item.scope && !item.product_title && (
                    <div className="text-[11px] text-slate-500">{item.scope}</div>
                  )}
                </td>
                <td className="px-4 py-3 text-center text-slate-600 font-mono text-[11px]">
                  <div>{item.packs ? `${item.packs} pack(s)` : '1 pack'}</div>
                  <div className="text-slate-400 text-[10px]">{item.timeline_days} days delivery</div>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="font-mono font-bold text-slate-900 text-sm block">
                    {formatMinor(item.price_minor, currency)}
                  </span>
                  {nativePrice && (
                    <span className="font-mono text-[10px] text-slate-500 block">
                      ({nativePrice})
                    </span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
