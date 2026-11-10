// src/components/payment/TransactionTable.tsx
import React, { useState } from 'react'
import type { Transaction } from '../../api/types'
import { formatMinor } from '../../lib/money'
import { timeAgo } from '../../lib/time'
import { Link } from 'react-router-dom'
import { ROUTES } from '../../lib/constants'

interface TransactionTableProps {
  transactions: Transaction[]
}

export const TransactionTable: React.FC<TransactionTableProps> = ({ transactions }) => {
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const copyText = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(key)
    setTimeout(() => setCopiedId(null), 1500)
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-xs">
        <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
          <tr>
            <th className="px-4 py-3 text-left">Tx ID</th>
            <th className="px-4 py-3 text-left">Plan</th>
            <th className="px-4 py-3 text-left">PayPal Order ID</th>
            <th className="px-4 py-3 text-left">Capture ID</th>
            <th className="px-4 py-3 text-right">Amount</th>
            <th className="px-4 py-3 text-center">Status</th>
            <th className="px-4 py-3 text-right">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {transactions.map((tx) => {
            const isCompleted = tx.status === 'COMPLETED'
            return (
              <tr key={tx.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 font-mono font-bold text-slate-800">#{tx.id}</td>
                <td className="px-4 py-3">
                  <Link
                    to={ROUTES.plan(tx.plan_id)}
                    className="text-paypal-600 hover:underline font-mono font-medium"
                  >
                    Plan #{tx.plan_id}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5 font-mono text-slate-700">
                    <span className="truncate max-w-[140px]" title={tx.paypal_order_id}>
                      {tx.paypal_order_id}
                    </span>
                    <button
                      type="button"
                      onClick={() => copyText(tx.paypal_order_id, `ord-${tx.id}`)}
                      className="text-[10px] text-slate-400 hover:text-paypal-600"
                      title="Copy Order ID"
                    >
                      {copiedId === `ord-${tx.id}` ? '✓' : '📋'}
                    </button>
                  </div>
                </td>
                <td className="px-4 py-3">
                  {tx.capture_id ? (
                    <div className="flex items-center gap-1.5 font-mono text-slate-700">
                      <span className="truncate max-w-[140px]" title={tx.capture_id}>
                        {tx.capture_id}
                      </span>
                      <button
                        type="button"
                        onClick={() => copyText(tx.capture_id!, `cap-${tx.id}`)}
                        className="text-[10px] text-slate-400 hover:text-paypal-600"
                        title="Copy Capture ID"
                      >
                        {copiedId === `cap-${tx.id}` ? '✓' : '📋'}
                      </button>
                    </div>
                  ) : (
                    <span className="text-slate-400 italic">Pending capture</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right font-mono font-bold text-slate-900 text-sm">
                  {formatMinor(tx.amount_minor, tx.currency)}
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      isCompleted
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                        : 'bg-amber-100 text-amber-800 border border-amber-200'
                    }`}
                  >
                    {tx.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-slate-500 font-mono text-[11px]">
                  {timeAgo(tx.created_at)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
