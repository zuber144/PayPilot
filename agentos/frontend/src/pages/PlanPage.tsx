// src/pages/PlanPage.tsx — plan details, PayGuard result, approve flow
import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'
import { Money } from '../components/Money'
import type { PayGuardRuleResult } from '../api/types'

function RuleRow({ rule }: { rule: PayGuardRuleResult }) {
  const icon = rule.passed ? '✅' : rule.severity === 'BLOCK' ? '🚫' : '⚠️'
  return (
    <li className={`rule-item ${rule.passed ? 'rule-pass' : 'rule-fail'}`}>
      <span>{icon}</span>
      <div>
        <strong>{rule.rule}</strong>
        <span className="text-muted"> ({rule.severity})</span>
        <div className="text-sm">{rule.reason}</div>
      </div>
    </li>
  )
}

export function PlanPage() {
  const { id } = useParams<{ id: string }>()
  const planId = parseInt(id ?? '0', 10)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [ackFlags, setAckFlags] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const { data: plan, isLoading } = useQuery({
    queryKey: ['plan', planId],
    queryFn: () => api.getPlan(planId),
    enabled: planId > 0,
  })

  const payguardMutation = useMutation({
    mutationFn: () => api.runPayGuard(planId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plan', planId] }),
    onError: (e: Error) => setError(e.message),
  })

  const approveMutation = useMutation({
    mutationFn: () => api.approvePlan(planId, { acknowledged_flags: ackFlags }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['plan', planId] }),
    onError: (e: Error) => setError(e.message),
  })

  if (isLoading) return <div className="container"><div className="spinner" /></div>
  if (!plan) return <div className="container">Plan not found.</div>

  const pg = plan.payguard_result
  const verdict = pg?.verdict
  const flags = pg?.flags ?? []
  const isBlocked = plan.status === 'BLOCKED' || verdict === 'BLOCKED'
  const isApproved = plan.status === 'APPROVED'
  const canApprove = plan.status === 'CHECKED' && !isBlocked
  const unackedFlags = flags.filter((f) => !ackFlags.includes(f))

  const toggleFlag = (flag: string) => {
    setAckFlags((prev) =>
      prev.includes(flag) ? prev.filter((f) => f !== flag) : [...prev, flag]
    )
  }

  return (
    <div className="container">
      <div className="flex items-center gap-2 mb-2">
        <h1>Plan #{plan.id}</h1>
        <StatusBadge status={plan.status} />
      </div>

      <div className="card">
        <h2>Plan Items</h2>
        <table>
          <thead>
            <tr><th>Need</th><th>Provider</th><th>Price</th><th>Timeline</th></tr>
          </thead>
          <tbody>
            {plan.items.map((item, i) => (
              <tr key={i}>
                <td>{item.need_key}</td>
                <td>{item.provider_name}</td>
                <td><Money minor={item.price_minor} currency={plan.currency} /></td>
                <td>{item.timeline_days}d</td>
              </tr>
            ))}
            <tr style={{ fontWeight: 'bold' }}>
              <td colSpan={2}>Total</td>
              <td><Money minor={plan.total_minor} currency={plan.currency} /></td>
              <td />
            </tr>
          </tbody>
        </table>
        {plan.rationale && (
          <p className="mt-2 text-sm text-muted"><em>{plan.rationale}</em></p>
        )}
      </div>

      {/* PayGuard section */}
      <div className="card">
        <h2>🛡️ PayGuard</h2>
        {!pg && (
          <div>
            <p className="text-muted text-sm mb-2">PayGuard check not yet run.</p>
            <button
              className="btn btn-primary"
              onClick={() => payguardMutation.mutate()}
              disabled={payguardMutation.isPending || plan.status !== 'DRAFT'}
            >
              {payguardMutation.isPending ? 'Running…' : 'Run PayGuard Check'}
            </button>
          </div>
        )}

        {pg && (
          <>
            <div className="flex items-center gap-1 mb-2">
              <strong>Verdict:</strong>
              <span className={`badge ${verdict === 'APPROVED' ? 'badge-green' : verdict === 'REVIEW' ? 'badge-yellow' : 'badge-red'}`}>
                {verdict}
              </span>
              {pg.risk_score != null && (
                <span className="text-sm text-muted">· Risk score: {pg.risk_score}/100</span>
              )}
            </div>

            {pg.flags.length > 0 && (
              <div className="mb-2">
                <strong className="text-sm">AI Flags:</strong>{' '}
                {pg.flags.map((f) => (
                  <span key={f} className="badge badge-yellow" style={{ marginRight: '0.25rem' }}>{f}</span>
                ))}
              </div>
            )}

            <p className="text-sm text-muted mb-2">{pg.summary}</p>

            <ul className="rule-list">
              {pg.rules.map((rule) => (
                <RuleRow key={rule.rule} rule={rule} />
              ))}
            </ul>
          </>
        )}
      </div>

      {/* Flag acknowledgement for REVIEW */}
      {canApprove && verdict === 'REVIEW' && flags.length > 0 && (
        <div className="card">
          <h2>⚠️ Acknowledge Flags Before Approval</h2>
          {flags.map((flag) => (
            <label key={flag} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                style={{ width: 'auto' }}
                checked={ackFlags.includes(flag)}
                onChange={() => toggleFlag(flag)}
              />
              {flag}
            </label>
          ))}
        </div>
      )}

      {error && <div className="error-box">{error}</div>}

      {/* Actions */}
      <div className="flex gap-1 mt-2">
        {canApprove && (
          <button
            className="btn btn-success"
            onClick={() => approveMutation.mutate()}
            disabled={
              approveMutation.isPending ||
              (verdict === 'REVIEW' && unackedFlags.length > 0)
            }
          >
            {approveMutation.isPending ? 'Approving…' : 'Approve Plan'}
          </button>
        )}
        {isApproved && (
          <Link to={`/plans/${plan.id}/pay`} className="btn btn-primary">
            💳 Proceed to Payment →
          </Link>
        )}
        {isBlocked && (
          <div className="badge badge-red" style={{ padding: '0.5rem 1rem' }}>
            🚫 Plan is BLOCKED — cannot approve or pay
          </div>
        )}
      </div>
    </div>
  )
}
