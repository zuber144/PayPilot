// src/components/payguard/FlagList.tsx
import React from 'react'

interface FlagListProps {
  flags: string[]
}

export const FlagList: React.FC<FlagListProps> = ({ flags }) => {
  if (!flags || flags.length === 0) {
    return (
      <div className="text-xs text-emerald-700 bg-emerald-50 p-3 rounded-lg border border-emerald-200 flex items-center gap-2">
        <span>✓</span>
        <span>Zero policy or behavioral risk flags detected.</span>
      </div>
    )
  }

  const flagDescriptions: Record<string, string> = {
    VENDOR_CONCENTRATION:
      'Single provider accounts for greater than 70% of total plan budget.',
    ML_RISK_MEDIUM:
      'AI scoring model detected abnormal pattern requiring human oversight.',
    UNVERIFIED_PROVIDER:
      'One or more proposed providers have not satisfied KYC or verification standards.',
    GOAL_ALIGNMENT_WARNING:
      'Proposed deliverables deviate slightly from declared goal requirements.',
    SPLIT_PAYMENT_RISK:
      'Transactions appear fragmented into smaller chunks near compliance thresholds.',
  }

  return (
    <div className="space-y-2">
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Identified Risk Flags ({flags.length})
      </span>
      <div className="space-y-2">
        {flags.map((flag) => (
          <div
            key={flag}
            className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-900 space-y-1"
          >
            <div className="font-mono font-bold flex items-center gap-1.5">
              <span>⚠</span>
              <span>{flag}</span>
            </div>
            <p className="text-slate-600">
              {flagDescriptions[flag] ?? 'Flag flagged for mandatory review before payment capture.'}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
