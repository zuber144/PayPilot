// src/components/payment/ReceiptCard.tsx
import React, { useState } from 'react'
import type { CaptureResponse } from '../../api/types'
import { formatMinor } from '../../lib/money'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Link } from 'react-router-dom'
import { ROUTES } from '../../lib/constants'

interface ReceiptCardProps {
  receipt: CaptureResponse
  orderId?: string
  planId?: number
}

export const ReceiptCard: React.FC<ReceiptCardProps> = ({ receipt, orderId, planId }) => {
  const [copied, setCopied] = useState<string | null>(null)

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    setCopied(label)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <Card padding="lg" className="max-w-xl mx-auto border-emerald-200 bg-white shadow-md space-y-6">
      {/* Header */}
      <div className="text-center space-y-2 pb-4 border-b border-slate-100">
        <div className="w-14 h-14 mx-auto rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-2xl font-bold">
          ✓
        </div>
        <h2 className="text-xl font-black text-slate-900 tracking-tight">Payment Settled Successfully</h2>
        <p className="text-xs text-slate-500">
          Funds captured via PayPal Orders API v2 (Sandbox). Your providers have been notified.
        </p>
      </div>

      {/* Amount banner */}
      <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 text-center">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-800">
          Settlement Amount Captured
        </span>
        <div className="text-3xl font-black font-mono text-emerald-900 mt-1">
          {formatMinor(receipt.amount_minor, receipt.currency)}
        </div>
      </div>

      {/* Metadata fields */}
      <div className="divide-y divide-slate-100 text-xs">
        <div className="py-2.5 flex items-center justify-between">
          <span className="text-slate-500 font-medium">Capture ID</span>
          <div className="flex items-center gap-1.5 font-mono font-semibold text-slate-900">
            <span>{receipt.capture_id ?? 'Pending'}</span>
            {receipt.capture_id && (
              <button
                type="button"
                onClick={() => copyToClipboard(receipt.capture_id!, 'capture')}
                className="text-[10px] text-paypal-600 hover:text-paypal-700 underline"
              >
                {copied === 'capture' ? 'Copied!' : 'Copy'}
              </button>
            )}
          </div>
        </div>

        {orderId && (
          <div className="py-2.5 flex items-center justify-between">
            <span className="text-slate-500 font-medium">PayPal Order ID</span>
            <div className="flex items-center gap-1.5 font-mono font-semibold text-slate-900">
              <span>{orderId}</span>
              <button
                type="button"
                onClick={() => copyToClipboard(orderId, 'order')}
                className="text-[10px] text-paypal-600 hover:text-paypal-700 underline"
              >
                {copied === 'order' ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>
        )}

        {planId && (
          <div className="py-2.5 flex items-center justify-between">
            <span className="text-slate-500 font-medium">Plan Reference</span>
            <Link
              to={ROUTES.plan(planId)}
              className="font-mono font-semibold text-paypal-600 hover:underline"
            >
              Plan #{planId}
            </Link>
          </div>
        )}

        <div className="py-2.5 flex items-center justify-between">
          <span className="text-slate-500 font-medium">Status</span>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
            {receipt.status}
          </span>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row gap-3 pt-2">
        <Link to={ROUTES.transactions} className="flex-1">
          <Button variant="outline" size="md" className="w-full">
            View All Transactions
          </Button>
        </Link>
        <Link to={ROUTES.home} className="flex-1">
          <Button variant="primary" size="md" className="w-full">
            Deploy New Agent →
          </Button>
        </Link>
      </div>
    </Card>
  )
}
