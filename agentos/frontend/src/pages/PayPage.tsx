// src/pages/PayPage.tsx — initiates PayPal payment for an APPROVED plan
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api'
import { Money } from '../components/Money'
import { StatusBadge } from '../components/StatusBadge'

export function PayPage() {
  const { id } = useParams<{ id: string }>()
  const planId = parseInt(id ?? '0', 10)
  const [error, setError] = useState<string | null>(null)
  const [approvalUrl, setApprovalUrl] = useState<string | null>(null)

  const { data: plan, isLoading } = useQuery({
    queryKey: ['plan', planId],
    queryFn: () => api.getPlan(planId),
    enabled: planId > 0,
  })

  const payMutation = useMutation({
    mutationFn: () => api.payPlan(planId),
    onSuccess: (data) => {
      setApprovalUrl(data.approval_url)
    },
    onError: (e: Error) => setError(e.message),
  })

  if (isLoading) return <div className="container"><div className="spinner" /></div>
  if (!plan) return <div className="container">Plan not found.</div>

  return (
    <div className="container">
      <h1>💳 Payment</h1>
      <div className="card">
        <h2>Plan #{plan.id} — <StatusBadge status={plan.status} /></h2>
        <p><strong>Total:</strong> <Money minor={plan.total_minor} currency={plan.currency} /></p>
        <p className="text-sm text-muted mt-1">
          Payment is processed securely via PayPal Sandbox.
          You will be redirected to PayPal to complete payment.
        </p>
      </div>

      {error && <div className="error-box">{error}</div>}

      {plan.status === 'APPROVED' && !approvalUrl && (
        <div className="card">
          <button
            className="btn btn-primary"
            onClick={() => payMutation.mutate()}
            disabled={payMutation.isPending}
            style={{ fontSize: '1rem', padding: '0.75rem 2rem' }}
          >
            {payMutation.isPending ? 'Creating PayPal Order…' : '🔒 Pay with PayPal →'}
          </button>
          <p className="text-sm text-muted mt-1">
            This will create a PayPal order for{' '}
            <strong><Money minor={plan.total_minor} currency={plan.currency} /></strong>.
            No charge until you approve on PayPal.
          </p>
        </div>
      )}

      {approvalUrl && (
        <div className="card">
          <h2>✅ Order Created</h2>
          <p className="text-sm mb-2">Your PayPal order has been created. Click below to complete payment on PayPal.</p>
          <a
            href={approvalUrl}
            className="btn btn-primary"
            style={{ fontSize: '1rem', padding: '0.75rem 2rem' }}
          >
            Complete Payment on PayPal →
          </a>
          <p className="text-sm text-muted mt-1">
            After approving, you'll be redirected back to complete the capture.
          </p>
        </div>
      )}

      {plan.status !== 'APPROVED' && plan.status !== 'PAYING' && (
        <div className="error-box">
          Plan must be APPROVED to initiate payment. Current status: {plan.status}
        </div>
      )}
    </div>
  )
}
