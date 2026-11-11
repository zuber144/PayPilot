// src/pages/GoalExecution.tsx (Screen 2)
import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useGoal, useGoalOffers } from '../api/hooks'
import { AgentTimeline } from '../components/trace/AgentTimeline'
import { OfferGroup } from '../components/offers/OfferGroup'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import { ErrorState } from '../components/ui/ErrorState'
import { formatMinor } from '../lib/money'
import { elapsedSince } from '../lib/time'
import { ROUTES, GOAL_STATUS_COLOR, GOAL_STATUS_LABEL } from '../lib/constants'

export const GoalExecution: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const goalId = id ? Number(id) : undefined

  // Poll while RUNNING
  const { data: goal, isLoading, error, refetch } = useGoal(goalId, { poll: true })
  const { data: offersData } = useGoalOffers(goalId)

  const [elapsed, setElapsed] = useState<string>('0s')

  useEffect(() => {
    if (!goal?.created_at) return
    const updateElapsed = () => setElapsed(elapsedSince(goal.created_at))
    updateElapsed()
    const timer = setInterval(updateElapsed, 1000)
    return () => clearInterval(timer)
  }, [goal?.created_at])

  if (isLoading) {
    return (
      <div className="py-24 text-center space-y-4">
        <Spinner size="lg" />
        <p className="text-sm text-slate-500 font-medium">Connecting to AgentOS execution pipeline…</p>
      </div>
    )
  }

  if (error || !goal) {
    return (
      <ErrorState
        title="Could not load goal execution"
        message={error?.message ?? 'Goal not found'}
        onRetry={() => refetch()}
      />
    )
  }

  const isRunning = goal.status === 'RUNNING'
  const isReady = goal.status === 'PLAN_READY' || Boolean(goal.plan_id)
  const offerGroups = offersData?.groups ?? []
  const needs = goal.parsed?.needs ?? []

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">
              Goal Execution #{goal.id}
            </h1>
            <span
              aria-live="polite"
              className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide flex items-center gap-1.5 ${
                GOAL_STATUS_COLOR[goal.status] || 'bg-slate-100 text-slate-700'
              }`}
            >
              {isRunning && <span className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />}
              {GOAL_STATUS_LABEL[goal.status] || goal.status}
            </span>
            {goal.scenario && (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-50 text-purple-700 border border-purple-200 uppercase">
                Scenario: {goal.scenario}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1 line-clamp-1 max-w-2xl">{goal.raw_text}</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right text-xs">
            <span className="text-slate-400 block text-[10px] uppercase font-semibold">Elapsed Time</span>
            <span className="font-mono font-bold text-slate-700">{elapsed}</span>
          </div>

          {isReady && goal.plan_id && (
            <Link to={ROUTES.plan(goal.plan_id)}>
              <Button variant="primary" size="md" className="shadow-md animate-fade-in">
                Inspect Generated Plan &amp; PayGuard &rarr;
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* If Goal requires clarification (NEEDS_INPUT) */}
      {goal.status === 'NEEDS_INPUT' && goal.question && (
        <Card padding="md" className="border-amber-300 bg-amber-50 space-y-2">
          <div className="flex items-center gap-2 font-bold text-amber-900 text-sm">
            <span>❓</span>
            <span>Agent Clarification Needed</span>
          </div>
          <p className="text-xs text-amber-800 leading-relaxed">{goal.question}</p>
        </Card>
      )}

      {/* Main Grid: Left = Timeline, Right = Parsed Requirements & Offers */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Progressive Agent Timeline */}
        <div className="lg:col-span-6 space-y-4">
          <Card padding="md">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Agent Trace &amp; Audit Log</h3>
                <p className="text-xs text-slate-500">Live multi-agent step execution and state transitions</p>
              </div>
              <span className="text-xs font-mono text-slate-500">{goal.trace.length} event(s)</span>
            </div>

            <AgentTimeline trace={goal.trace} isRunning={isRunning} />
          </Card>
        </div>

        {/* Right: Parsed Requirements & Real-time Offers */}
        <div className="lg:col-span-6 space-y-5">
          {/* Parsed Goal Summary */}
          <Card padding="md" className="space-y-3 bg-white">
            <h3 className="font-bold text-slate-900 text-sm border-b border-slate-100 pb-2">
              Parsed Procurement Specifications
            </h3>

            {goal.parsed ? (
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Declared Needs</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {needs.map((n, idx) => {
                      const needKey = typeof n === 'string' ? n : n.key
                      return (
                        <span
                          key={`${needKey}-${idx}`}
                          className="px-2 py-0.5 rounded bg-slate-100 text-navy-600 font-mono text-[11px] font-semibold"
                        >
                          {needKey.replace('_', ' ')}
                        </span>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Budget Ceiling</span>
                  <div className="font-mono font-bold text-slate-900 text-sm mt-1">
                    {formatMinor(goal.budget_minor, goal.currency)}
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Deadline</span>
                  <div className="font-semibold text-slate-800 mt-1">
                    {goal.parsed.deadline_days ? `${goal.parsed.deadline_days} days` : 'Flexible'}
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Currency</span>
                  <div className="font-mono text-slate-800 mt-1">
                    {goal.currency}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-slate-400 py-3 italic">
                Parsing goal requirements in step 1…
              </div>
            )}
          </Card>

          {/* Negotiated Offers Grouped by Need */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Autonomous Provider Negotiations
              </h3>
              <span className="text-xs text-slate-400">
                {offerGroups.length === 0 ? 'Negotiating…' : `${offerGroups.length} need category(ies)`}
              </span>
            </div>

            {offerGroups.length === 0 ? (
              <Card padding="md" className="text-center text-xs text-slate-400 py-8">
                Provider agents will place bids and counter-offers once discovery completes.
              </Card>
            ) : (
              offerGroups.map((group) => (
                <OfferGroup
                  key={group.need_key}
                  needKey={group.need_key}
                  offers={group.offers}
                  currency={goal.currency}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
