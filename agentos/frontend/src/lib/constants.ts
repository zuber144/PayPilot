// src/lib/constants.ts — status → color/label mappings and route paths

import type { GoalStatus, PlanStatus, Verdict, TraceStatus, RuleResult } from '../api/types'

// ─── Route paths ──────────────────────────────────────────────────────────────
export const ROUTES = {
  home: '/',
  goal: (id: number | string) => `/goals/${id}`,
  plan: (id: number | string) => `/plans/${id}`,
  pay: (id: number | string) => `/plans/${id}/pay`,
  payReturn: '/payment/return',
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

// ─── Scenario chips ──────────────────────────────────────────────────────────
export interface ScenarioChip {
  id: string
  label: string
  description: string
  goalText: string
  budgetMinor: number
  currency: string
  badge: 'APPROVED' | 'REVIEW' | 'BLOCKED' | 'RETRY'
}

export const DEMO_SCENARIOS: ScenarioChip[] = [
  {
    id: 'approved',
    label: '✅ Clean Approval',
    description: 'All 10 PayGuard rules pass, risk score low',
    goalText: 'Build a professional website with compelling copy for our SaaS product launch',
    budgetMinor: 500000,  // $5,000
    currency: 'USD',
    badge: 'APPROVED',
  },
  {
    id: 'review',
    label: '⚠️ Review Required',
    description: 'Single-vendor concentration flag needs acknowledgement',
    goalText: 'Create a logo for my startup in 3 days',
    budgetMinor: 15000,  // $150
    currency: 'USD',
    badge: 'REVIEW',
  },
  {
    id: 'blocked',
    label: '🚫 Policy Block',
    description: 'Unverified provider triggers BLOCKED verdict',
    goalText: 'Write blog posts using the cheapest possible copywriters no matter what',
    budgetMinor: 10000,  // $100
    currency: 'USD',
    badge: 'BLOCKED',
  },
  {
    id: 'retry',
    label: '🔄 Retry & Fallback',
    description: 'Discovery retries once, provider agent uses fallback',
    goalText: 'Build a landing page and social media graphics for a product launch campaign',
    budgetMinor: 200000,  // $2,000
    currency: 'USD',
    badge: 'RETRY',
  },
]
