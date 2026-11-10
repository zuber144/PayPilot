// src/components/payguard/PolicyChecklist.tsx
import React, { useState } from 'react'
import type { PayGuardRuleResult } from '../../api/types'

interface PolicyChecklistProps {
  rules: PayGuardRuleResult[]
}

export const PolicyChecklist: React.FC<PolicyChecklistProps> = ({ rules }) => {
  const [expandedRule, setExpandedRule] = useState<string | null>(null)

  const toggleExpand = (id: string) => {
    setExpandedRule(expandedRule === id ? null : id)
  }

  const resultStyles = {
    PASS: {
      badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
      icon: '✓',
      text: 'PASS',
    },
    REVIEW: {
      badge: 'bg-amber-100 text-amber-800 border-amber-200',
      icon: '⚠',
      text: 'REVIEW',
    },
    BLOCK: {
      badge: 'bg-red-100 text-red-800 border-red-200',
      icon: '✕',
      text: 'BLOCK',
    },
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Deterministic Safety Rules ({rules.length})
        </h4>
        <span className="text-[11px] text-slate-400">Click row for audit detail</span>
      </div>

      <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl bg-white overflow-hidden shadow-xs">
        {rules.map((rule) => {
          const ruleId = rule.id || rule.rule || 'UNKNOWN_RULE'
          const ruleResult = rule.result || (rule.passed ? 'PASS' : rule.severity || 'BLOCK')
          const style = resultStyles[ruleResult as keyof typeof resultStyles] || resultStyles.PASS
          const isExpanded = expandedRule === ruleId
          const detailText = rule.detail || rule.reason || 'Audit check verified successfully.'

          return (
            <div key={ruleId} className="transition-colors hover:bg-slate-50/60">
              <div
                onClick={() => toggleExpand(ruleId)}
                className="px-4 py-3 flex items-center justify-between gap-3 cursor-pointer select-none text-xs"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border ${style.badge}`}
                  >
                    {style.icon}
                  </span>
                  <span className="font-mono font-semibold text-slate-800 truncate">
                    {ruleId}
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${style.badge}`}>
                    {style.text}
                  </span>
                  <span className="text-slate-400 text-[10px]">{isExpanded ? '▲' : '▼'}</span>
                </div>
              </div>

              {isExpanded && (
                <div className="px-4 pb-3 pt-1 text-xs text-slate-600 bg-slate-50/70 border-t border-slate-100">
                  <p className="leading-relaxed">{detailText}</p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
