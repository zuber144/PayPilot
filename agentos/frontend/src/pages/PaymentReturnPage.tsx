// src/pages/PaymentReturnPage.tsx — called after PayPal redirects back
// Captures the payment and shows a receipt
import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { api } from '../api'
import { formatMoney } from '../components/Money'
import type { CaptureResponse } from '../api/types'

export function PaymentReturnPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') // PayPal order ID
  const planId = parseInt(searchParams.get('plan_id') ?? '0', 10)
  const [result, setResult] = useState<CaptureResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token || !planId) {
      setError('Missing token or plan_id in return URL.')
      setLoading(false)
      return
    }
    api
      .capturePayment(token, planId)
      .then((r) => {
        setResult(r)
        setLoading(false)
      })
      .catch((e: Error) => {
        setError(e.message)
        setLoading(false)
      })
  }, [token, planId])

  if (loading) {
    return (
      <div className="container">
        <div className="spinner" />
        <p className="mt-2">Capturing payment…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container">
        <div className="error-box">❌ Payment capture failed: {error}</div>
        <Link to={`/plans/${planId}`} className="btn btn-secondary mt-2">← Back to Plan</Link>
      </div>
    )
  }

  if (!result) return null

  return (
    <div className="container">
      <div className="card" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '3rem' }}>🎉</div>
        <h1>Payment Complete!</h1>
        <p className="text-muted mt-1">Your plan has been paid successfully.</p>

        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '1.5rem', margin: '1.5rem 0' }}>
          <div><strong>Amount:</strong> {formatMoney(result.amount_minor, result.currency)}</div>
          <div><strong>Capture ID:</strong> <span className="font-mono">{result.capture_id}</span></div>
          <div><strong>Status:</strong> <span className="badge badge-green">{result.status}</span></div>
        </div>

        <div className="flex gap-1" style={{ justifyContent: 'center' }}>
          <Link to="/transactions" className="btn btn-secondary">View Transactions</Link>
          <Link to="/" className="btn btn-primary">New Goal →</Link>
        </div>
      </div>
    </div>
  )
}
