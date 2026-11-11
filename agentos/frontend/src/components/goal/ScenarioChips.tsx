// src/components/goal/ScenarioChips.tsx
import React from 'react'
import { DEMO_SCENARIOS, type ScenarioChip } from '../../lib/constants'

interface ScenarioChipsProps {
  onSelect: (scenario: ScenarioChip) => void
  selectedId?: string
}

export const ScenarioChips: React.FC<ScenarioChipsProps> = ({ onSelect, selectedId }) => {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Demo Scenarios
        </label>
        <span className="text-xs text-slate-400">Click to autofill</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {DEMO_SCENARIOS.map((scenario) => {
          const isSelected = selectedId === scenario.id

          const badgeColor = {
            APPROVED: 'bg-emerald-100 text-emerald-800 border-emerald-200',
            REVIEW: 'bg-amber-100 text-amber-800 border-amber-200',
            BLOCKED: 'bg-red-100 text-red-800 border-red-200',
            RETRY: 'bg-blue-100 text-blue-800 border-blue-200',
          }[scenario.badge]

          return (
            <button
              key={scenario.id}
              type="button"
              onClick={() => onSelect(scenario)}
              className={`text-left p-3 rounded-lg border transition-all text-xs focus:outline-none focus:ring-2 focus:ring-paypal-500 ${
                isSelected
                  ? 'border-paypal-500 bg-paypal-50 ring-1 ring-paypal-500 shadow-sm'
                  : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center justify-between gap-1.5 mb-1">
                <span className="font-semibold text-slate-800">{scenario.label}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${badgeColor}`}>
                  {scenario.badge}
                </span>
              </div>
              <p className="text-slate-500 line-clamp-2 leading-relaxed">{scenario.description}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}
