// src/pages/PaymentPage.tsx (Screen 4)
import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { usePlan, useApprovePlan, usePayPlan } from '../api/hooks'
import { ApprovalPanel } from '../components/payment/ApprovalPanel'
import { PlanSummary } from '../components/plan/PlanSummary'
import { LineItemTable } from '../components/plan/LineItemTable'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { ErrorState } from '../components/ui/ErrorState'
import { useToast } from '../components/ui/Toast'

export const PaymentPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const planId = id ? Number(id) : undefined
  const navigate = useNavigate()
  const { showToast } = useToast()

  const { data: plan, isLoading, error, refetch } = usePlan(planId)
  const approvePlan = useApprovePlan(planId)
  const payPlan = usePayPlan(planId)

  if (isLoading) {
    return (
      <div className="py-24 text-center space-y-4">
        <Spinner size="lg" />
        <p className="text-sm text-slate-500 font-medium">Preparing Payment Gateway…</p>
      </div>
    )
  }

  if (error || !plan) {
    return (
      <ErrorState
        title="Could not load payment checkout"
        message={error?.message ?? 'Plan not found'}
        onRetry={() => refetch()}
      />
    )
  }

  const handleApproveAndPay = async (acknowledgedFlags: string[]) => {
    try {
      // Step 1: Approve plan with acknowledged flags
      await approvePlan.mutateAsync({ acknowledged_flags: acknowledgedFlags })
      showToast('Plan approved. Initiating PayPal settlement…', 'info')

      // Step 2: Pay plan -> returns PayPal order + approval_url
      const payRes = await payPlan.mutateAsync()

      // Redirect to approval_url (in mock mode this is /payment/return?token=...; in real mode PayPal Sandbox)
      if (payRes.approval_url.startsWith('http')) {
        window.location.href = payRes.approval_url
      } else {
        navigate(payRes.approval_url)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Payment authorization failed'
      showToast(msg, 'error')
    }
  }

  const isSubmitting = approvePlan.isPending || payPlan.isPending

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Payment Authorization</h1>
        <p className="text-sm text-slate-500 mt-1">
          Final human-in-the-loop sign-off before releasing autonomous escrow via PayPal Orders API v2.
        </p>
      </div>

      <PlanSummary plan={plan} />

      <Card padding="md" className="space-y-3">
        <h3 className="font-bold text-slate-900 text-sm border-b border-slate-100 pb-2">
          Settlement Breakdown
        </h3>
        <LineItemTable items={plan.items} currency={plan.currency} />
      </Card>

      <ApprovalPanel
        plan={plan}
        onApprove={handleApproveAndPay}
        isSubmitting={isSubmitting}
      />
    </div>
  )
}
