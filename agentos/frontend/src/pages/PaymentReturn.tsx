// src/pages/PaymentReturn.tsx (Screen 5)
import React, { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useCapturePayment } from '../api/hooks'
import { ReceiptCard } from '../components/payment/ReceiptCard'
import { Spinner } from '../components/ui/Spinner'
import { ErrorState } from '../components/ui/ErrorState'
import type { CaptureResponse } from '../api/types'

export const PaymentReturn: React.FC = () => {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || searchParams.get('order_id')
  const planIdStr = searchParams.get('plan_id')
  const planId = planIdStr ? Number(planIdStr) : 1

  const capturePayment = useCapturePayment()
  const [receipt, setReceipt] = useState<CaptureResponse | null>(null)
  const [captureError, setCaptureError] = useState<string | null>(null)

  // Guard against React StrictMode double invocation
  const hasCaptured = useRef(false)

  useEffect(() => {
    if (!token) {
      setCaptureError('Missing payment authorization token in return parameters.')
      return
    }

    if (hasCaptured.current) return
    hasCaptured.current = true

    // Check if we already have this receipt in session storage to make repeat visits idempotent
    const cachedReceipt = sessionStorage.getItem(`receipt_${token}`)
    if (cachedReceipt) {
      try {
        setReceipt(JSON.parse(cachedReceipt))
        return
      } catch {
        // Ignore parse error and proceed to capture
      }
    }

    capturePayment
      .mutateAsync({ token, planId })
      .then((res) => {
        setReceipt(res)
        sessionStorage.setItem(`receipt_${token}`, JSON.stringify(res))
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : 'Failed to capture payment with PayPal'
        setCaptureError(msg)
      })
  }, [token, planId, capturePayment])

  if (captureError) {
    return (
      <div className="py-12">
        <ErrorState
          title="Payment Settlement Unsuccessful"
          message={captureError}
          onRetry={() => {
            hasCaptured.current = false
            window.location.reload()
          }}
        />
      </div>
    )
  }

  if (!receipt) {
    return (
      <div className="py-32 text-center space-y-4">
        <Spinner size="lg" />
        <h2 className="text-lg font-bold text-slate-800">Finalizing PayPal Settlement…</h2>
        <p className="text-xs text-slate-500 font-mono">
          Capturing funds for Order <span className="font-semibold text-slate-700">{token}</span>
        </p>
      </div>
    )
  }

  return (
    <div className="py-6">
      <ReceiptCard receipt={receipt} orderId={token ?? undefined} planId={planId} />
    </div>
  )
}
