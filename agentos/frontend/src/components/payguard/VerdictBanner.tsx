// src/components/payguard/VerdictBanner.tsx
import React from 'react'
import type { Verdict } from '../../api/types'

interface VerdictBannerProps {
  verdict: Verdict
  aiOk?: boolean
}

export const VerdictBanner: React.FC<VerdictBannerProps> = ({ verdict, aiOk = true }) => {
  const configs = {
    APPROVED: {
      bg: 'bg-emerald-50 border-emerald-200 text-emerald-900',
      iconBg: 'bg-emerald-500 text-white',
      icon: '✓',
      title: 'PayGuard Verdict: APPROVED',
      subtitle:
        'All deterministic safety rules passed and ML risk score is within acceptable bounds. Ready for payment settlement.',
    },
    REVIEW: {
      bg: 'bg-amber-50 border-amber-200 text-amber-900',
      iconBg: 'bg-amber-500 text-white',
      icon: '⚠',
      title: 'PayGuard Verdict: HUMAN REVIEW REQUIRED',
      subtitle:
        'One or more non-blocking risk flags were identified (e.g. single vendor concentration). A human must acknowledge each flag before releasing funds.',
    },
    BLOCKED: {
      bg: 'bg-red-50 border-red-200 text-red-900',
      iconBg: 'bg-red-600 text-white',
      icon: '✕',
      title: 'PayGuard Verdict: BLOCKED BY POLICY',
      subtitle:
        'A critical safety rule was violated (e.g. unverified provider, budget breach, or high AI risk). Payment authorization is blocked.',
    },
  }[verdict]

  return (
    <div className={`rounded-xl border p-5 shadow-xs ${configs.bg} animate-fade-in`}>
      <div className="flex items-start gap-4">
        <div
          className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xl shadow-xs shrink-0 ${configs.iconBg}`}
        >
          {configs.icon}
        </div>
        <div className="flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-bold tracking-tight">{configs.title}</h3>
            {!aiOk && (
              <span className="text-xs px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-medium">
                AI Risk Offline (Fallback Active)
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm mt-1 opacity-90 leading-relaxed">{configs.subtitle}</p>
        </div>
      </div>
    </div>
  )
}
