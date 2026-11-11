// src/api/types.ts — TypeScript types matching backend/app/schemas.py & enums.py

// ─── Enums & Trace ────────────────────────────────────────────────────────────
export type GoalStatus = 'RUNNING' | 'NEEDS_INPUT' | 'PLAN_READY' | 'FAILED'
export type PlanStatus =
  | 'DRAFT'
  | 'CHECKED'
  | 'USER_APPROVED'
  | 'PAYING'
  | 'PAID'
  | 'FAILED'
  // Legacy backward-compat
  | 'APPROVED'
  | 'BLOCKED'
  | 'PAY_FAILED'

export type Verdict = 'APPROVED' | 'REVIEW' | 'BLOCKED'
export type RuleResult = 'PASS' | 'REVIEW' | 'BLOCK'
export type OfferStatus = 'OPEN' | 'COUNTERED' | 'ACCEPTED' | 'REJECTED' | 'SELECTED'
export type TraceStatus = 'OK' | 'RETRY' | 'FALLBACK' | 'ERROR'
export type TraceNode =
  | 'orchestrator'
  | 'goal'
  | 'discovery'
  | 'provider'
  | 'negotiation'
  | 'planning'
  | 'payguard'

export type TxnStatus = 'CREATED' | 'APPROVED' | 'COMPLETED' | 'FAILED'
export type Scenario = 'clean' | 'retry' | 'blocked' | 'review'

export interface TraceEvent {
  seq?: number
  ts?: string
  node?: TraceNode | string
  action?: string
  status: TraceStatus
  summary: string
  reason?: string
  duration_ms: number
  data?: Record<string, unknown>
  // Backward compatibility
  step?: string
  used_fallback?: boolean
  retry_count?: number
  hash?: string
}

// ─── Needs & Parsed Goal ───────────────────────────────────────────────────────
export interface Need {
  key: string
  category: string
  quantity?: number | null
  must_haves?: string[]
}

export interface ParsedGoal {
  needs: (Need | string)[]
  deadline_days?: number | null
  currency: string
}

export interface Goal {
  id: number
  status: GoalStatus
  raw_text: string
  budget_minor: number
  currency: string
  scenario?: Scenario | null
  parsed: ParsedGoal | null
  question?: string | null
  trace: TraceEvent[]
  plan_id: number | null
  created_at: string
  user_id?: number
}

// ─── Providers ─────────────────────────────────────────────────────────────────
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
  currency?: string
  persona?: string
  demo?: boolean
}

// ─── Offers (Matching new backend OffersOut & OfferGroup) ─────────────────────
export interface OfferRound {
  round: number
  price_minor: number
  counter_minor?: number | null
  status: OfferStatus
  scope: string
}

export interface ProviderOffers {
  provider_id: number
  provider_name: string
  verified: boolean
  rating: number
  timeline_days: number
  opening_price_minor: number
  final_price_minor: number
  status: OfferStatus
  rounds: OfferRound[]
}

export interface OfferGroup {
  need_key: string
  offers: ProviderOffers[]
}

export interface OffersOut {
  goal_id: number
  groups: OfferGroup[]
}

// Flat offer representation for compatibility
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

// ─── PayGuard & Policies ───────────────────────────────────────────────────────
export interface PayGuardRuleResult {
  id: string
  result: RuleResult
  detail: string
  // Legacy aliases
  rule?: string
  passed?: boolean
  reason?: string
  severity?: 'BLOCK' | 'REVIEW' | 'INFO'
}

export interface Flag {
  id: string
  source: string // "POLICY" | "AI"
  message: string
  requires_ack: boolean
}

export interface PayGuardResult {
  verdict: Verdict
  risk_score?: number | null // float 0.0–1.0
  ai_ok: boolean
  flags: (Flag | string)[]
  rules: PayGuardRuleResult[]
  checked_at?: string | null
  summary?: string
}

// ─── Plans ─────────────────────────────────────────────────────────────────────
export interface PlanItem {
  need_key: string
  provider_id: number
  provider_name: string
  price_minor: number
  timeline_days: number
  verified: boolean
  currency?: string
  scope?: string
  offer_id?: number
}

export interface Plan {
  id: number
  goal_id: number
  status: PlanStatus
  currency: string
  total_minor: number
  budget_minor?: number
  rationale: string
  items: PlanItem[]
  payguard: PayGuardResult | null
  payguard_result?: PayGuardResult | null
  acknowledged_flags?: string[]
  approved_at?: string | null
}

// ─── Transactions ──────────────────────────────────────────────────────────────
export interface Transaction {
  id: number
  plan_id: number
  goal_id?: number | null
  goal_summary?: string | null
  paypal_order_id: string
  capture_id?: string | null
  amount_minor: number
  currency: string
  status: TxnStatus | string
  created_at: string
}

// ─── Requests & Responses ─────────────────────────────────────────────────────
export interface CreateGoalRequest {
  raw_text: string
  budget_minor: number
  currency?: string
  scenario?: Scenario | null
  user_id?: number
}

export interface GoalCreated {
  id: number
  status: GoalStatus
}

export interface ApproveRequest {
  acknowledged_flags: string[]
}

export interface PayResponse {
  plan_id: number
  paypal_order_id: string
  approval_url: string
  status: PlanStatus | string
  reused?: boolean
  transaction_id?: number
}

export interface CaptureRequest {
  paypal_order_id: string
}

export interface CaptureResponse {
  id?: number
  transaction_id?: number
  capture_id?: string | null
  paypal_order_id?: string
  amount_minor: number
  currency: string
  status: string
}

// ─── Helper Functions ─────────────────────────────────────────────────────────
export function getPayGuard(plan: Plan): PayGuardResult | null {
  return plan.payguard ?? plan.payguard_result ?? null
}

export function getFlagId(flag: Flag | string): string {
  return typeof flag === 'string' ? flag : flag.id
}

export function getFlagMessage(flag: Flag | string): string {
  return typeof flag === 'string' ? flag : flag.message
}

export function isFlagAckRequired(flag: Flag | string): boolean {
  return typeof flag === 'string' ? true : flag.requires_ack
}
