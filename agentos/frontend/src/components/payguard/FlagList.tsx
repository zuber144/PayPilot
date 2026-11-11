// src/components/payguard/FlagList.tsx
import React from 'react'
import type { Flag } from '../../api/types'
import { getFlagId, getFlagMessage, isFlagAckRequired } from '../../api/types'

interface FlagListProps {
  flags: (Flag | string)[]
}

export const FlagList: React.FC<FlagListProps> = ({ flags = [] }) => {
  if (!flags || flags.length === 0) {
    return (
      <div className="text-xs text-emerald-700 bg-emerald-50 p-3 rounded-lg border border-emerald-200 flex items-center gap-2">
        <span>✓</span>
        <span>Zero policy or behavioral risk flags detected.</span>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Identified Risk Flags ({flags.length})
      </span>
      <div className="space-y-2">
        {flags.map((flag, idx) => {
          const id = getFlagId(flag)
          const msg = getFlagMessage(flag)
          const requiresAck = isFlagAckRequired(flag)

          return (
            <div
              key={`${id}-${idx}`}
              className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-xs text-amber-900 space-y-1"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="font-mono font-bold flex items-center gap-1.5">
                  <span>⚠</span>
                  <span>{id}</span>
                </div>
                {requiresAck && (
                  <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-amber-200 text-amber-900">
                    Ack Required
                  </span>
                )}
              </div>
              <p className="text-slate-600 leading-relaxed">{msg}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
