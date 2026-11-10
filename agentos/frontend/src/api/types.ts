// src/api/types.ts — shared TypeScript types mirroring backend schemas (Addendum-updated)

// ─── Trace ────────────────────────────────────────────────────────────────────
export type TraceNode =
  | 'orchestrator'
  | 'goal'
  | 'discovery'
  | 'provider'
  | 'negotiation'
  | 'planning'
  | 'payguard'

export type TraceStatus = 'OK' | 'RETRY' | 'FALLBACK' | 'ERROR'

export interface TraceEvent {
  step: string
  node?: TraceNode
  summary: string
  duration_ms: number
  status: TraceStatus
  used_fallback: boolean
  retry_count?: number
  prev_hash?: string
  hash?: string
  detail?: Record<string, unknown>
}

// ─── Goal ─────────────────────────────────────────────────────────────────────
export type GoalStatus = 'RUNNING' | 'NEEDS_INPUT' | 'PLAN_READY' | 'FAILED'

export interface ParsedGoal {
  needs: string[]
  budget_minor: number
  currency: string
  deadline_days: number
}

export interface Goal {
  id: number
  user_id: number
  raw_text: string
  parsed: ParsedGoal | null
  budget_minor: number
  currency: string
  status: GoalStatus
  trace: TraceEvent[]
  created_at: string
  plan_id: number | null
}

// ─── Provider ─────────────────────────────────────────────────────────────────
export interface Provider {
  id: number
  name: string
  category: string
  base_price_minor: number
  min_price_minor: number
  concession_rate: number
  rating: number
  turnaround_days: number
  verified: boolean
  persona: string
}

// ─── Offer ────────────────────────────────────────────────────────────────────
export type OfferStatus = 'OPEN' | 'COUNTERED' | 'ACCEPTED' | 'REJECTED' | 'SELECTED'

export interface Offer {
  id: number
  goal_id: number
  provider_id: number
  need_key: string
  round: number
  price_minor: number
  scope: string
  timeline_days: number
  status: OfferStatus
}

// ─── PayGuard ─────────────────────────────────────────────────────────────────
export type RuleResult = 'PASS' | 'REVIEW' | 'BLOCK'
export type Verdict = 'APPROVED' | 'REVIEW' | 'BLOCKED'

export interface PayGuardRuleResult {
  id: string         // e.g. BUDGET_CAP, ML_RISK, GOAL_ALIGNMENT …
  rule?: string      // legacy alias
  result: RuleResult
  passed?: boolean   // legacy alias: result === 'PASS'
  severity?: 'BLOCK' | 'REVIEW' | 'INFO'
  detail: string
  reason?: string    // legacy alias for detail
}

export interface PayGuardResult {
  verdict: Verdict
  risk_score: number | null  // 0.0–1.0 float; null if AI unavailable
  ai_ok: boolean
  flags: string[]
  rules: PayGuardRuleResult[]
  summary?: string
}

// ─── Plan ─────────────────────────────────────────────────────────────────────
export type PlanStatus =
  | 'DRAFT'
  | 'CHECKED'
  | 'USER_APPROVED'
  | 'PAYING'
  | 'PAID'
  | 'FAILED'
  // Legacy values still returned by backend
  | 'APPROVED'
  | 'BLOCKED'
  | 'PAY_FAILED'

export interface PlanItem {
  need_key: string
  provider_id: number
  provider_name: string
  price_minor: number
  scope: string
  timeline_days: number
  offer_id: number
}

export interface Plan {
  id: number
  goal_id: number
  items: PlanItem[]
  total_minor: number
  currency: string
  rationale: string
  payguard: PayGuardResult | null
  payguard_result?: PayGuardResult | null  // legacy alias
  status: PlanStatus
  approved_at: string | null
}

// ─── Transaction ──────────────────────────────────────────────────────────────
export interface Transaction {
  id: number
  plan_id: number
  paypal_order_id: string
  capture_id: string | null
  amount_minor: number
  currency: string
  status: string
  created_at: string
}

// ─── API request / response shapes ───────────────────────────────────────────
export interface CreateGoalRequest {
  raw_text: string
  budget_minor: number
  currency: string
  user_id: number
}

export interface ApproveRequest {
  acknowledged_flags: string[]
}

export interface PayResponse {
  transaction_id: number
  paypal_order_id: string
  approval_url: string
  status: string
}

export interface CaptureResponse {
  transaction_id: number
  capture_id: string
  amount_minor: number
  currency: string
  status: string
}

// Helper: get the unified payguard result regardless of key name
export function getPayGuard(plan: Plan): PayGuardResult | null {
  return plan.payguard ?? plan.payguard_result ?? null
}
