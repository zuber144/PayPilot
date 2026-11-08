// src/api/types.ts — shared TypeScript types mirroring backend schemas

export interface TraceEvent {
  step: string
  summary: string
  duration_ms: number
  status: 'ok' | 'error' | 'fallback'
  used_fallback: boolean
}

export interface Goal {
  id: number
  user_id: number
  raw_text: string
  parsed: ParsedGoal | null
  budget_minor: number
  currency: string
  status: 'NEW' | 'RUNNING' | 'PLANNED' | 'FAILED'
  trace: TraceEvent[]
  created_at: string
  plan_id: number | null
}

export interface ParsedGoal {
  needs: string[]
  budget_minor: number
  currency: string
  deadline_days: number
}

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

export interface Offer {
  id: number
  goal_id: number
  provider_id: number
  need_key: string
  round: number
  price_minor: number
  scope: string
  timeline_days: number
  status: 'OPENING' | 'COUNTERED' | 'FINAL' | 'SELECTED'
}

export interface PlanItem {
  need_key: string
  provider_id: number
  provider_name: string
  price_minor: number
  scope: string
  timeline_days: number
  offer_id: number
}

export interface PayGuardRuleResult {
  rule: string
  passed: boolean
  severity: 'BLOCK' | 'REVIEW' | 'INFO'
  reason: string
}

export interface PayGuardResult {
  verdict: 'APPROVED' | 'REVIEW' | 'BLOCKED'
  rules: PayGuardRuleResult[]
  risk_score: number | null
  flags: string[]
  summary: string
}

export interface Plan {
  id: number
  goal_id: number
  items: PlanItem[]
  total_minor: number
  currency: string
  rationale: string
  payguard_result: PayGuardResult | null
  status: 'DRAFT' | 'CHECKED' | 'APPROVED' | 'PAYING' | 'PAID' | 'BLOCKED' | 'PAY_FAILED'
  approved_at: string | null
}

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

export interface CreateGoalRequest {
  raw_text: string
  budget_minor: number
  currency: string
  user_id: number
}

export interface ApproveRequest {
  acknowledged_flags: string[]
}
