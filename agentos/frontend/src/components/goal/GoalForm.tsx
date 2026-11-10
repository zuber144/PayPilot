// src/components/goal/GoalForm.tsx
import React, { useState } from 'react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { ScenarioChips } from './ScenarioChips'
import type { ScenarioChip } from '../../lib/constants'
import type { CreateGoalRequest } from '../../api/types'

interface GoalFormProps {
  onSubmit: (data: CreateGoalRequest) => void
  isSubmitting?: boolean
}

export const GoalForm: React.FC<GoalFormProps> = ({ onSubmit, isSubmitting }) => {
  const [goalText, setGoalText] = useState('')
  const [budgetMajor, setBudgetMajor] = useState<number>(5000)
  const [currency, setCurrency] = useState<'USD' | 'INR'>('USD')
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | undefined>()
  const [error, setError] = useState<string | null>(null)

  const handleScenarioSelect = (scenario: ScenarioChip) => {
    setSelectedScenarioId(scenario.id)
    setGoalText(scenario.goalText)
    setBudgetMajor(scenario.budgetMinor / 100)
    setCurrency(scenario.currency as 'USD' | 'INR')
    setError(null)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!goalText.trim()) {
      setError('Please describe your procurement goal.')
      return
    }
    if (budgetMajor <= 0) {
      setError('Budget must be greater than zero.')
      return
    }

    setError(null)
    onSubmit({
      raw_text: goalText.trim(),
      budget_minor: Math.round(budgetMajor * 100),
      currency,
      user_id: 1, // Demo user
    })
  }

  return (
    <Card padding="lg" className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Deploy Autonomous Agent</h2>
        <p className="text-sm text-slate-500 mt-1">
          Specify what you need. AgentOS will discover providers, negotiate competitive offers, and build a verified execution plan.
        </p>
      </div>

      <ScenarioChips onSelect={handleScenarioSelect} selectedId={selectedScenarioId} />

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="goalText" className="block text-sm font-semibold text-slate-800 mb-1.5">
            Goal Statement
          </label>
          <textarea
            id="goalText"
            rows={4}
            value={goalText}
            onChange={(e) => {
              setGoalText(e.target.value)
              setSelectedScenarioId(undefined)
              if (error) setError(null)
            }}
            placeholder="e.g. Build a modern landing page for a B2B SaaS startup with copywriting and brand graphics within 2 weeks"
            className="w-full rounded-lg border-slate-300 shadow-sm focus:border-paypal-500 focus:ring-paypal-500 text-sm p-3 transition-colors"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="budget" className="block text-sm font-semibold text-slate-800 mb-1.5">
              Maximum Budget ({currency})
            </label>
            <div className="relative rounded-lg shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 text-sm">
                {currency === 'INR' ? '₹' : '$'}
              </div>
              <input
                id="budget"
                type="number"
                min="1"
                step="any"
                value={budgetMajor}
                onChange={(e) => setBudgetMajor(parseFloat(e.target.value) || 0)}
                className="w-full pl-8 pr-3 py-2 rounded-lg border-slate-300 text-sm focus:border-paypal-500 focus:ring-paypal-500 font-mono"
              />
            </div>
          </div>

          <div>
            <label htmlFor="currency" className="block text-sm font-semibold text-slate-800 mb-1.5">
              Currency
            </label>
            <select
              id="currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value as 'USD' | 'INR')}
              className="w-full py-2 px-3 rounded-lg border-slate-300 text-sm focus:border-paypal-500 focus:ring-paypal-500 bg-white"
            >
              <option value="USD">USD ($) — PayPal Sandbox Default</option>
              <option value="INR">INR (₹) — Indian Rupee (Paise)</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="text-xs text-red-600 bg-red-50 p-2.5 rounded-lg border border-red-200">
            {error}
          </div>
        )}

        <Button
          type="submit"
          variant="primary"
          size="lg"
          isLoading={isSubmitting}
          className="w-full font-semibold shadow-md"
        >
          {isSubmitting ? 'Dispatching Agents…' : 'Start Agent Pipeline →'}
        </Button>
      </form>
    </Card>
  )
}
