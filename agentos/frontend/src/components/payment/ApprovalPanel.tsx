// src/components/payment/ApprovalPanel.tsx
import React, { useState } from 'react'
import type { Plan, Flag } from '../../api/types'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { useKillSwitch } from '../../context/KillSwitchContext'
import { getPayGuard, getFlagId, getFlagMessage, isFlagAckRequired } from '../../api/types'

interface ApprovalPanelProps {
  plan: Plan
  onApprove: (acknowledgedFlags: string[]) => void
  isSubmitting?: boolean
}

export const ApprovalPanel: React.FC<ApprovalPanelProps> = ({
  plan,
  onApprove,
  isSubmitting = false,
}) => {
  const { paymentsEnabled } = useKillSwitch()
  const payguard = getPayGuard(plan)
  const verdict = payguard?.verdict ?? 'APPROVED'
  const flags = payguard?.flags ?? []

  // Filter flags that require explicit acknowledgment
  const ackRequiredFlags = flags.filter(isFlagAckRequired)

  // Track acknowledged flags by their string id
  const [acknowledged, setAcknowledged] = useState<Record<string, boolean>>({})
  const [authorized, setAuthorized] = useState(false)

  const isBlocked = verdict === 'BLOCKED'
  const isReview = verdict === 'REVIEW'

  // If review, all ack-required flags must be checked
  const allFlagsAcknowledged =
    ackRequiredFlags.length === 0 ||
    ackRequiredFlags.every((f) => acknowledged[getFlagId(f)])

  const canSubmit = !isBlocked && paymentsEnabled && authorized && allFlagsAcknowledged

  const handleToggleFlag = (id: string) => {
    setAcknowledged((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    const acknowledgedList = Object.keys(acknowledged).filter((k) => acknowledged[k])
    onApprove(acknowledgedList)
  }

  return (
    <Card padding="lg" className="space-y-5 border-slate-200">
      <div>
        <h3 className="text-base font-bold text-slate-900">Authorization &amp; Settlement</h3>
        <p className="text-xs text-slate-500 mt-0.5">
          Review policy flags and authorize autonomous settlement through PayPal Sandbox.
        </p>
      </div>

      {!paymentsEnabled && (
        <div className="p-3 bg-red-100 border border-red-300 rounded-lg text-xs text-red-900 font-semibold flex items-center gap-2">
          <span>🛑</span>
          <span>Global Payment Kill Switch is ENGAGED. Settlement is currently disabled.</span>
        </div>
      )}

      {isBlocked && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800">
          This plan is <strong>BLOCKED</strong> by PayGuard AI safety policies. You cannot approve or pay this plan until policy violations are remediated.
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* If REVIEW, render per-flag checkboxes for flags requiring ack */}
        {isReview && ackRequiredFlags.length > 0 && (
          <div className="space-y-2 p-3 bg-amber-50/70 border border-amber-200 rounded-lg">
            <span className="text-xs font-semibold text-amber-900 block">
              Mandatory Risk Acknowledgment:
            </span>
            {ackRequiredFlags.map((flag) => {
              const id = getFlagId(flag)
              const msg = getFlagMessage(flag)
              return (
                <label
                  key={id}
                  className="flex items-start gap-2.5 text-xs text-slate-700 cursor-pointer select-none"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(acknowledged[id])}
                    onChange={() => handleToggleFlag(id)}
                    className="mt-0.5 rounded border-slate-300 text-paypal-500 focus:ring-paypal-500"
                  />
                  <span>
                    I acknowledge and accept: <strong className="font-mono text-amber-950">{id}</strong> — {msg}
                  </span>
                </label>
              )
            })}
          </div>
        )}

        {/* Master authorization checkbox */}
        <label className="flex items-start gap-2.5 text-xs text-slate-800 cursor-pointer select-none pt-2">
          <input
            type="checkbox"
            checked={authorized}
            disabled={isBlocked || !paymentsEnabled}
            onChange={(e) => setAuthorized(e.target.checked)}
            className="mt-0.5 rounded border-slate-300 text-paypal-500 focus:ring-paypal-500 disabled:opacity-50"
          />
          <span className="leading-relaxed">
            I confirm that the deliverables and quoted amounts match my procurement specifications, and I authorize PayPilot to initiate payment via PayPal Sandbox.
          </span>
        </label>

        <Button
          type="submit"
          variant={isBlocked ? 'danger' : 'primary'}
          size="lg"
          disabled={!canSubmit}
          isLoading={isSubmitting}
          className="w-full font-semibold shadow-md"
        >
          {isBlocked
            ? 'Blocked by PayGuard'
            : isSubmitting
            ? 'Processing Settlement…'
            : 'Approve & Pay with PayPal →'}
        </Button>
      </form>
    </Card>
  )
}
