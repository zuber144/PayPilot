// src/pages/PlanPage.tsx (Screen 3)
import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { usePlan, useGoal } from '../api/hooks'
import { VerdictBanner } from '../components/payguard/VerdictBanner'
import { RiskGauge } from '../components/payguard/RiskGauge'
import { FlagList } from '../components/payguard/FlagList'
import { PolicyChecklist } from '../components/payguard/PolicyChecklist'
import { BlockCard } from '../components/payguard/BlockCard'
import { PlanSummary } from '../components/plan/PlanSummary'
import { LineItemTable } from '../components/plan/LineItemTable'
import { BudgetBar } from '../components/plan/BudgetBar'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import { ErrorState } from '../components/ui/ErrorState'
import { ROUTES } from '../lib/constants'
import { getPayGuard } from '../api/types'

export const PlanPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const planId = id ? Number(id) : undefined

  const { data: plan, isLoading, error, refetch } = usePlan(planId)
  const { data: goal } = useGoal(plan?.goal_id)

  if (isLoading) {
    return (
      <div className="py-24 text-center space-y-4">
        <Spinner size="lg" />
        <p className="text-sm text-slate-500 font-medium">Evaluating Plan &amp; PayGuard AI Audit…</p>
      </div>
    )
  }

  if (error || !plan) {
    return (
      <ErrorState
        title="Could not load plan"
        message={error?.message ?? 'Plan not found'}
        onRetry={() => refetch()}
      />
    )
  }

  const payguard = getPayGuard(plan)
  const verdict = payguard?.verdict ?? 'APPROVED'
  const isBlocked = verdict === 'BLOCKED'
  const isPaid = plan.status === 'PAID'

  return (
    <div className="space-y-6">
      {/* Top Full-Width PayGuard Verdict Banner */}
      <VerdictBanner verdict={verdict} aiOk={payguard?.ai_ok ?? true} />

      {/* Main Grid: Left = Plan Details, Right = PayGuard AI Safety Checks */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Plan Summary, Items, Budget, Rationale */}
        <div className="lg:col-span-7 space-y-5">
          <PlanSummary plan={plan} />

          {/* Line Items Table */}
          <Card padding="md" className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="font-bold text-slate-900 text-sm">Selected Deliverables</h3>
              <span className="text-xs text-slate-500 font-mono">
                {plan.items.length} line item(s)
              </span>
            </div>
            <LineItemTable items={plan.items} currency={plan.currency} />
          </Card>

          {/* Budget Utilization Bar */}
          {goal && (
            <Card padding="md">
              <BudgetBar
                totalMinor={plan.total_minor}
                budgetMinor={goal.budget_minor}
                currency={plan.currency}
              />
            </Card>
          )}

          {/* Agent Rationale */}
          <Card padding="md" className="space-y-2">
            <h3 className="font-bold text-slate-900 text-sm">Planning Agent Rationale</h3>
            <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
              {plan.rationale}
            </p>
          </Card>
        </div>

        {/* Right Column: Risk Gauge, Flags, Deterministic Rules, Action Button */}
        <div className="lg:col-span-5 space-y-5">
          {payguard && (
            <>
              <RiskGauge score={payguard.risk_score} aiOk={payguard.ai_ok} />
              <FlagList flags={payguard.flags} />
              <PolicyChecklist rules={payguard.rules} />
            </>
          )}

          {/* If BLOCKED: Show remediation block card */}
          {isBlocked && (
            <BlockCard planId={plan.id} onFixApplied={() => refetch()} />
          )}

          {/* Bottom Action Area */}
          <Card padding="md" className="space-y-3 text-center bg-white">
            {isPaid ? (
              <div className="p-3 bg-emerald-50 rounded-lg text-xs font-semibold text-emerald-800 border border-emerald-200">
                ✓ Plan has been paid and settled.
              </div>
            ) : isBlocked ? (
              <Button variant="danger" size="lg" disabled className="w-full">
                Payment Blocked by Policy
              </Button>
            ) : (
              <Link to={ROUTES.pay(plan.id)} className="block">
                <Button variant="primary" size="lg" className="w-full font-bold shadow-md">
                  Authorize &amp; Pay Plan &rarr;
                </Button>
              </Link>
            )}

            <div className="text-[11px] text-slate-400">
              {isBlocked
                ? 'Address policy violations above to enable payment settlement'
                : 'Redirects to PayPal sandbox authorization'}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
