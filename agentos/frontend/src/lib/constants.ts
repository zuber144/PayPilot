// src/lib/constants.ts — status → color/label mappings and route paths matching backend/app/enums.py

import type { GoalStatus, PlanStatus, Verdict, TraceStatus, RuleResult, Scenario } from '../api/types'

// ─── Route paths ──────────────────────────────────────────────────────────────
export const ROUTES = {
  home: '/',
  goal: (id: number | string) => `/goals/${id}`,
  plan: (id: number | string) => `/plans/${id}`,
  pay: (id: number | string) => `/plans/${id}/pay`,
  payReturn: '/payments/return',
  transactions: '/transactions',
} as const

// ─── Goal status ──────────────────────────────────────────────────────────────
export const GOAL_STATUS_LABEL: Record<GoalStatus, string> = {
  RUNNING: 'Running',
  NEEDS_INPUT: 'Needs Input',
  PLAN_READY: 'Plan Ready',
  FAILED: 'Failed',
}

export const GOAL_STATUS_COLOR: Record<GoalStatus, string> = {
  RUNNING: 'bg-blue-100 text-blue-800',
  NEEDS_INPUT: 'bg-amber-100 text-amber-800',
  PLAN_READY: 'bg-green-100 text-green-800',
  FAILED: 'bg-red-100 text-red-800',
}

// ─── Plan status ──────────────────────────────────────────────────────────────
export const PLAN_STATUS_LABEL: Record<string, string> = {
  DRAFT: 'Draft',
  CHECKED: 'Checked',
  USER_APPROVED: 'Approved',
  APPROVED: 'Approved',
  PAYING: 'Paying…',
  PAID: 'Paid',
  FAILED: 'Failed',
  BLOCKED: 'Blocked',
  PAY_FAILED: 'Payment Failed',
}

export const PLAN_STATUS_COLOR: Record<string, string> = {
  DRAFT: 'bg-slate-100 text-slate-700',
  CHECKED: 'bg-blue-100 text-blue-800',
  USER_APPROVED: 'bg-emerald-100 text-emerald-800',
  APPROVED: 'bg-emerald-100 text-emerald-800',
  PAYING: 'bg-purple-100 text-purple-800',
  PAID: 'bg-green-100 text-green-800',
  FAILED: 'bg-red-100 text-red-800',
  BLOCKED: 'bg-red-100 text-red-800',
  PAY_FAILED: 'bg-red-100 text-red-800',
}

// ─── Verdict ──────────────────────────────────────────────────────────────────
export const VERDICT_COLOR: Record<Verdict, string> = {
  APPROVED: 'bg-emerald-50 border-emerald-300 text-emerald-800',
  REVIEW: 'bg-amber-50 border-amber-300 text-amber-800',
  BLOCKED: 'bg-red-50 border-red-300 text-red-800',
}

export const VERDICT_ICON: Record<Verdict, string> = {
  APPROVED: '✅',
  REVIEW: '⚠️',
  BLOCKED: '🚫',
}

// ─── Trace status ─────────────────────────────────────────────────────────────
export const TRACE_STATUS_COLOR: Record<TraceStatus, string> = {
  OK: 'text-emerald-600',
  RETRY: 'text-amber-600',
  FALLBACK: 'text-slate-500',
  ERROR: 'text-red-600',
}

// ─── Rule result ──────────────────────────────────────────────────────────────
export const RULE_RESULT_COLOR: Record<RuleResult, string> = {
  PASS: 'text-emerald-600',
  REVIEW: 'text-amber-600',
  BLOCK: 'text-red-600',
}

export const RULE_RESULT_ICON: Record<RuleResult, string> = {
  PASS: '✓',
  REVIEW: '⚠',
  BLOCK: '✗',
}

// ─── Scenario chips (Matching backend/app/enums.py Scenario values) ────────────
export interface ScenarioChip {
  id: string
  scenario: Scenario
  label: string
  description: string
  goalText: string
  budgetMinor: number
  currency: string
  badge: 'APPROVED' | 'REVIEW' | 'BLOCKED' | 'RETRY'
}

export const DEMO_SCENARIOS: ScenarioChip[] = [
  {
    id: 'clean',
    scenario: 'clean',
    label: '✅ Clean Approval',
    description: 'All 10 PayGuard rules pass; verified providers within budget ($40,966.66)',
    goalText: 'Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days',
    budgetMinor: 5000000, // $50,000
    currency: 'USD',
    badge: 'APPROVED',
  },
  {
    id: 'retry',
    scenario: 'retry',
    label: '🔄 Retry Scenario',
    description: 'Strict filters trigger RETRY trace event; preference filters relaxed; plan succeeds',
    goalText: 'Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days',
    budgetMinor: 5000000, // $50,000
    currency: 'USD',
    badge: 'RETRY',
  },
  {
    id: 'blocked',
    scenario: 'blocked',
    label: '🚫 Blocked Scenario',
    description: 'Low budget forces unverified provider (QuickBites Co); PayGuard blocks settlement',
    goalText: 'Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days',
    budgetMinor: 3600000, // $36,000
    currency: 'USD',
    badge: 'BLOCKED',
  },
  {
    id: 'review',
    scenario: 'review',
    label: '⚠️ Review Required',
    description: 'Single provider holds 100% (> 70%); requires mandatory human flag acknowledgment',
    goalText: 'Catering for 100 people for our office event in 10 days',
    budgetMinor: 5000000, // $50,000
    currency: 'USD',
    badge: 'REVIEW',
  },
]
