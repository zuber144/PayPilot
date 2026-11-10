// src/mocks/fixtures.ts — rich fixture data for all 4 demo scenarios
// Switch on with VITE_USE_MOCKS=true

import type {
  Goal, Offer, Plan, Provider, Transaction, TraceEvent, PayGuardRuleResult
} from '../api/types'

// ─── Providers ────────────────────────────────────────────────────────────────
export const mockProviders: Provider[] = [
  { id: 1, name: 'PixelCraft Studio',   category: 'web_design',    base_price_minor: 300000, min_price_minor: 180000, concession_rate: 0.15, rating: 4.8, turnaround_days: 10, verified: true,  persona: 'Professional web design agency.' },
  { id: 2, name: 'DevForge Labs',       category: 'web_design',    base_price_minor: 250000, min_price_minor: 170000, concession_rate: 0.10, rating: 4.5, turnaround_days: 14, verified: true,  persona: 'Full-stack dev shop.' },
  { id: 3, name: 'WordSmith Pro',       category: 'copywriting',   base_price_minor: 80000,  min_price_minor: 50000,  concession_rate: 0.12, rating: 4.6, turnaround_days: 5,  verified: true,  persona: 'Award-winning copywriters.' },
  { id: 4, name: 'ContentHive',         category: 'copywriting',   base_price_minor: 50000,  min_price_minor: 30000,  concession_rate: 0.20, rating: 3.9, turnaround_days: 4,  verified: false, persona: 'Budget content farm.' },
  { id: 5, name: 'BrandMaster',         category: 'logo_design',   base_price_minor: 60000,  min_price_minor: 40000,  concession_rate: 0.10, rating: 4.7, turnaround_days: 7,  verified: true,  persona: 'Premium brand identity studio.' },
  { id: 6, name: 'LogoRocket',          category: 'logo_design',   base_price_minor: 25000,  min_price_minor: 15000,  concession_rate: 0.15, rating: 4.2, turnaround_days: 3,  verified: true,  persona: 'Fast-turnaround logo shop.' },
  { id: 7, name: 'SocialPulse Agency',  category: 'social_media',  base_price_minor: 120000, min_price_minor: 80000,  concession_rate: 0.08, rating: 4.4, turnaround_days: 6,  verified: true,  persona: 'Social media growth specialists.' },
  { id: 8, name: 'ViralVault',          category: 'social_media',  base_price_minor: 90000,  min_price_minor: 60000,  concession_rate: 0.12, rating: 4.1, turnaround_days: 5,  verified: true,  persona: 'Viral content creators.' },
]

// ─── Scenario: Clean Approval (goal 1) ────────────────────────────────────────
const traceApproved: TraceEvent[] = [
  { step: 'orchestrator', node: 'orchestrator', summary: 'Pipeline started for goal #1',               duration_ms: 5,  status: 'OK',       used_fallback: false },
  { step: 'goal_analyzer', node: 'goal',        summary: 'Identified 2 needs: web_design, copywriting', duration_ms: 42, status: 'OK',       used_fallback: false },
  { step: 'discovery',     node: 'discovery',   summary: 'Found 4 providers across 2 needs',           duration_ms: 18, status: 'OK',       used_fallback: false },
  { step: 'provider_agents', node: 'provider',  summary: 'PixelCraft → $2,500 | WordSmith → $680',      duration_ms: 65, status: 'OK',       used_fallback: false },
  { step: 'negotiation',   node: 'negotiation', summary: 'Round 2: saved $320 total',                  duration_ms: 28, status: 'OK',       used_fallback: false },
  { step: 'plan_generator', node: 'planning',   summary: 'Plan: 2 items, total $3,180, score=0.84',    duration_ms: 24, status: 'OK',       used_fallback: false },
  { step: 'payguard',      node: 'payguard',    summary: 'All 10 rules PASS — APPROVED',               duration_ms: 11, status: 'OK',       used_fallback: false },
  { step: 'orchestrator',  node: 'orchestrator', summary: 'Pipeline complete — plan ready',            duration_ms: 3,  status: 'OK',       used_fallback: false },
]

const rulesApproved: PayGuardRuleResult[] = [
  { id: 'BUDGET_CAP',          result: 'PASS', detail: 'Plan total $3,180 ≤ goal budget $5,000' },
  { id: 'TXN_LIMIT',           result: 'PASS', detail: 'Plan total $3,180 ≤ max limit $10,000' },
  { id: 'VERIFIED_PROVIDER',   result: 'PASS', detail: 'All 2 providers are verified ✓' },
  { id: 'CURRENCY_MATCH',      result: 'PASS', detail: "Currency 'USD' is valid ISO-4217" },
  { id: 'NO_DUPLICATE',        result: 'PASS', detail: 'No live transaction exists for this plan' },
  { id: 'PRICE_FLOOR',         result: 'PASS', detail: 'All item prices ≥ provider minimum floors' },
  { id: 'TOTAL_INTEGRITY',     result: 'PASS', detail: 'Sum of items (318000) matches plan total (318000)' },
  { id: 'GOAL_ALIGNMENT',      result: 'PASS', detail: 'All items map to declared goal needs' },
  { id: 'ML_RISK',             result: 'PASS', detail: 'Risk score 0.18 < 0.40 threshold — low risk' },
  { id: 'SINGLE_VENDOR_SHARE', result: 'PASS', detail: 'Max vendor share 79% — below 95% block threshold' },
]

export const mockGoalApproved: Goal = {
  id: 1, user_id: 1,
  raw_text: 'Build a professional website with compelling copy for our SaaS product launch',
  parsed: { needs: ['web_design', 'copywriting'], budget_minor: 500000, currency: 'USD', deadline_days: 21 },
  budget_minor: 500000, currency: 'USD', status: 'PLAN_READY',
  trace: traceApproved, created_at: '2026-11-10T08:00:00Z', plan_id: 1,
}

export const mockPlanApproved: Plan = {
  id: 1, goal_id: 1,
  items: [
    { need_key: 'web_design',  provider_id: 1, provider_name: 'PixelCraft Studio', price_minor: 230000, scope: 'Full responsive website (5 pages)', timeline_days: 10, offer_id: 1 },
    { need_key: 'copywriting', provider_id: 3, provider_name: 'WordSmith Pro',      price_minor: 88000,  scope: 'Homepage + 4 feature page copy',   timeline_days: 5,  offer_id: 2 },
  ],
  total_minor: 318000, currency: 'USD',
  rationale: 'PixelCraft Studio and WordSmith Pro provide the best quality-to-price ratio within your budget. Combined timeline of 10 days meets your deadline. Both providers are verified with ratings above 4.5.',
  payguard: { verdict: 'APPROVED', risk_score: 0.18, ai_ok: true, flags: [], rules: rulesApproved },
  status: 'CHECKED', approved_at: null,
}

// ─── Scenario: Review Required (goal 2) ───────────────────────────────────────
const traceReview: TraceEvent[] = [
  { step: 'orchestrator', node: 'orchestrator', summary: 'Pipeline started for goal #2',    duration_ms: 4,  status: 'OK', used_fallback: false },
  { step: 'goal_analyzer', node: 'goal',        summary: 'Identified 1 need: logo_design',  duration_ms: 38, status: 'OK', used_fallback: false },
  { step: 'discovery',    node: 'discovery',    summary: 'Found 2 providers: LogoRocket, BrandMaster', duration_ms: 15, status: 'OK', used_fallback: false },
  { step: 'provider_agents', node: 'provider',  summary: 'LogoRocket → $200; BrandMaster out-of-budget', duration_ms: 55, status: 'OK', used_fallback: false },
  { step: 'negotiation',  node: 'negotiation',  summary: 'Round 1 accepted: $170 final',    duration_ms: 20, status: 'OK', used_fallback: false },
  { step: 'plan_generator', node: 'planning',   summary: 'Plan: 1 item, total $170',         duration_ms: 18, status: 'OK', used_fallback: false },
  { step: 'payguard',     node: 'payguard',     summary: 'SINGLE_VENDOR_SHARE → REVIEW',     duration_ms: 9,  status: 'OK', used_fallback: false },
  { step: 'orchestrator', node: 'orchestrator', summary: 'Plan ready — human review needed', duration_ms: 2,  status: 'OK', used_fallback: false },
]

const rulesReview: PayGuardRuleResult[] = [
  { id: 'BUDGET_CAP',          result: 'PASS',   detail: 'Plan total $170 ≤ goal budget $150 ← note: within 115%' },
  { id: 'TXN_LIMIT',           result: 'PASS',   detail: 'Plan total $170 ≤ max limit $10,000' },
  { id: 'VERIFIED_PROVIDER',   result: 'PASS',   detail: 'LogoRocket is verified ✓' },
  { id: 'CURRENCY_MATCH',      result: 'PASS',   detail: "Currency 'USD' is valid ISO-4217" },
  { id: 'NO_DUPLICATE',        result: 'PASS',   detail: 'No live transaction exists for this plan' },
  { id: 'PRICE_FLOOR',         result: 'PASS',   detail: 'Price $170 ≥ floor $150' },
  { id: 'TOTAL_INTEGRITY',     result: 'PASS',   detail: 'Sum of items (17000) matches plan total (17000)' },
  { id: 'GOAL_ALIGNMENT',      result: 'PASS',   detail: 'Item maps to declared need: logo_design' },
  { id: 'ML_RISK',             result: 'REVIEW', detail: 'Risk score 0.42 ≥ 0.40 threshold — medium risk flag' },
  { id: 'SINGLE_VENDOR_SHARE', result: 'REVIEW', detail: 'Single vendor holds 100% — vendor concentration risk' },
]

export const mockGoalReview: Goal = {
  id: 2, user_id: 1,
  raw_text: 'Create a logo for my startup in 3 days',
  parsed: { needs: ['logo_design'], budget_minor: 15000, currency: 'USD', deadline_days: 3 },
  budget_minor: 15000, currency: 'USD', status: 'PLAN_READY',
  trace: traceReview, created_at: '2026-11-10T09:00:00Z', plan_id: 2,
}

export const mockPlanReview: Plan = {
  id: 2, goal_id: 2,
  items: [
    { need_key: 'logo_design', provider_id: 6, provider_name: 'LogoRocket', price_minor: 17000, scope: '3 logo concepts + revisions', timeline_days: 3, offer_id: 3 },
  ],
  total_minor: 17000, currency: 'USD',
  rationale: 'Only LogoRocket fits the budget and 3-day deadline. BrandMaster quoted $400, well above budget.',
  payguard: { verdict: 'REVIEW', risk_score: 0.42, ai_ok: true, flags: ['VENDOR_CONCENTRATION', 'ML_RISK_MEDIUM'], rules: rulesReview },
  status: 'CHECKED', approved_at: null,
}

// ─── Scenario: Blocked (goal 3) ───────────────────────────────────────────────
const traceBlocked: TraceEvent[] = [
  { step: 'orchestrator',   node: 'orchestrator', summary: 'Pipeline started for goal #3',    duration_ms: 4,  status: 'OK', used_fallback: false },
  { step: 'goal_analyzer',  node: 'goal',         summary: 'Identified 1 need: copywriting',  duration_ms: 35, status: 'OK', used_fallback: false },
  { step: 'discovery',      node: 'discovery',    summary: 'Found 2 providers; cheapest selected', duration_ms: 14, status: 'OK', used_fallback: false },
  { step: 'provider_agents', node: 'provider',    summary: 'ContentHive → $110 (unverified)',  duration_ms: 48, status: 'OK', used_fallback: false },
  { step: 'negotiation',    node: 'negotiation',  summary: 'Round 1: $100 accepted',           duration_ms: 18, status: 'OK', used_fallback: false },
  { step: 'plan_generator', node: 'planning',     summary: 'Plan: 1 item, total $100',          duration_ms: 15, status: 'OK', used_fallback: false },
  { step: 'payguard',       node: 'payguard',     summary: 'VERIFIED_PROVIDER → BLOCKED ✗',    duration_ms: 7,  status: 'OK', used_fallback: false },
  { step: 'orchestrator',   node: 'orchestrator', summary: 'Pipeline complete — plan BLOCKED', duration_ms: 2,  status: 'OK', used_fallback: false },
]

const rulesBlocked: PayGuardRuleResult[] = [
  { id: 'BUDGET_CAP',          result: 'PASS',  detail: 'Plan total $100 ≤ goal budget $100' },
  { id: 'TXN_LIMIT',           result: 'PASS',  detail: 'Plan total $100 ≤ max limit $10,000' },
  { id: 'VERIFIED_PROVIDER',   result: 'BLOCK', detail: 'ContentHive is NOT verified — cannot pay unverified providers' },
  { id: 'CURRENCY_MATCH',      result: 'PASS',  detail: "Currency 'USD' is valid ISO-4217" },
  { id: 'NO_DUPLICATE',        result: 'PASS',  detail: 'No live transaction exists for this plan' },
  { id: 'PRICE_FLOOR',         result: 'PASS',  detail: 'Price $100 ≥ floor $30' },
  { id: 'TOTAL_INTEGRITY',     result: 'PASS',  detail: 'Sum of items (10000) matches plan total (10000)' },
  { id: 'GOAL_ALIGNMENT',      result: 'PASS',  detail: 'Item maps to declared need: copywriting' },
  { id: 'ML_RISK',             result: 'PASS',  detail: 'Risk score 0.22 < 0.40 threshold' },
  { id: 'SINGLE_VENDOR_SHARE', result: 'PASS',  detail: 'Single vendor 100% — below block threshold' },
]

export const mockGoalBlocked: Goal = {
  id: 3, user_id: 1,
  raw_text: 'Write blog posts using the cheapest possible copywriters no matter what',
  parsed: { needs: ['copywriting'], budget_minor: 10000, currency: 'USD', deadline_days: 7 },
  budget_minor: 10000, currency: 'USD', status: 'PLAN_READY',
  trace: traceBlocked, created_at: '2026-11-10T10:00:00Z', plan_id: 3,
}

export const mockPlanBlocked: Plan = {
  id: 3, goal_id: 3,
  items: [
    { need_key: 'copywriting', provider_id: 4, provider_name: 'ContentHive', price_minor: 10000, scope: '5 blog posts (800 words each)', timeline_days: 4, offer_id: 4 },
  ],
  total_minor: 10000, currency: 'USD',
  rationale: 'ContentHive was the only provider within budget, but it is not verified.',
  payguard: { verdict: 'BLOCKED', risk_score: 0.22, ai_ok: true, flags: ['UNVERIFIED_PROVIDER'], rules: rulesBlocked },
  status: 'CHECKED', approved_at: null,
}

// ─── Scenario: Retry + Fallback (goal 4) ─────────────────────────────────────
const traceRetry: TraceEvent[] = [
  { step: 'orchestrator',   node: 'orchestrator', summary: 'Pipeline started for goal #4',           duration_ms: 5,  status: 'OK',       used_fallback: false },
  { step: 'goal_analyzer',  node: 'goal',         summary: 'Identified 2 needs: web_design, social_media', duration_ms: 40, status: 'OK', used_fallback: false },
  { step: 'discovery',      node: 'discovery',    summary: 'API timeout — retrying…',                 duration_ms: 5002, status: 'RETRY', used_fallback: false, retry_count: 1 },
  { step: 'discovery',      node: 'discovery',    summary: 'Retry OK: found 4 providers across 2 needs', duration_ms: 22, status: 'OK',  used_fallback: false },
  { step: 'provider_agents', node: 'provider',    summary: 'DevForge → $1,800 (fallback pricing)',    duration_ms: 80, status: 'FALLBACK', used_fallback: true },
  { step: 'provider_agents', node: 'provider',    summary: 'SocialPulse → $950',                      duration_ms: 60, status: 'OK',       used_fallback: false },
  { step: 'negotiation',    node: 'negotiation',  summary: 'Round 2: saved $280 total',              duration_ms: 32, status: 'OK',       used_fallback: false },
  { step: 'plan_generator', node: 'planning',     summary: 'Plan: 2 items, total $2,470',             duration_ms: 22, status: 'OK',       used_fallback: false },
  { step: 'payguard',       node: 'payguard',     summary: 'All rules PASS — APPROVED',              duration_ms: 10, status: 'OK',       used_fallback: false },
  { step: 'orchestrator',   node: 'orchestrator', summary: 'Pipeline complete (1 retry, 1 fallback)', duration_ms: 3,  status: 'OK',       used_fallback: false },
]

const rulesRetry: PayGuardRuleResult[] = [
  { id: 'BUDGET_CAP',          result: 'PASS', detail: 'Plan total $2,470 ≤ goal budget $2,000 ← note: 123% (within grace)' },
  { id: 'TXN_LIMIT',           result: 'PASS', detail: 'Plan total $2,470 ≤ max limit $10,000' },
  { id: 'VERIFIED_PROVIDER',   result: 'PASS', detail: 'All 2 providers are verified ✓' },
  { id: 'CURRENCY_MATCH',      result: 'PASS', detail: "Currency 'USD' is valid ISO-4217" },
  { id: 'NO_DUPLICATE',        result: 'PASS', detail: 'No live transaction exists for this plan' },
  { id: 'PRICE_FLOOR',         result: 'PASS', detail: 'All item prices ≥ provider minimum floors' },
  { id: 'TOTAL_INTEGRITY',     result: 'PASS', detail: 'Sum of items (247000) matches plan total (247000)' },
  { id: 'GOAL_ALIGNMENT',      result: 'PASS', detail: 'All items map to declared goal needs' },
  { id: 'ML_RISK',             result: 'PASS', detail: 'Risk score 0.26 < 0.40 threshold — low risk' },
  { id: 'SINGLE_VENDOR_SHARE', result: 'PASS', detail: 'Max vendor share 73% — below 95% block threshold' },
]

export const mockGoalRetry: Goal = {
  id: 4, user_id: 1,
  raw_text: 'Build a landing page and social media graphics for a product launch campaign',
  parsed: { needs: ['web_design', 'social_media'], budget_minor: 200000, currency: 'USD', deadline_days: 14 },
  budget_minor: 200000, currency: 'USD', status: 'PLAN_READY',
  trace: traceRetry, created_at: '2026-11-10T11:00:00Z', plan_id: 4,
}

export const mockPlanRetry: Plan = {
  id: 4, goal_id: 4,
  items: [
    { need_key: 'web_design',   provider_id: 2, provider_name: 'DevForge Labs',      price_minor: 170000, scope: 'Landing page (responsive, Webflow)', timeline_days: 10, offer_id: 5 },
    { need_key: 'social_media', provider_id: 7, provider_name: 'SocialPulse Agency', price_minor: 77000,  scope: '10 graphics + copy for 3 platforms', timeline_days: 6,  offer_id: 6 },
  ],
  total_minor: 247000, currency: 'USD',
  rationale: 'DevForge Labs (fallback pricing applied after timeout) and SocialPulse Agency deliver the full scope within 10 days. Slight budget overage accommodated by policy grace.',
  payguard: { verdict: 'APPROVED', risk_score: 0.26, ai_ok: true, flags: [], rules: rulesRetry },
  status: 'CHECKED', approved_at: null,
}

// ─── Offers (all goals) ───────────────────────────────────────────────────────
export const mockOffers: Offer[] = [
  // Goal 1 — web_design
  { id: 1, goal_id: 1, provider_id: 1, need_key: 'web_design',   round: 1, price_minor: 300000, scope: 'Full web design', timeline_days: 10, status: 'OPEN' },
  { id: 2, goal_id: 1, provider_id: 1, need_key: 'web_design',   round: 2, price_minor: 230000, scope: 'Full web design', timeline_days: 10, status: 'SELECTED' },
  // Goal 1 — copywriting
  { id: 3, goal_id: 1, provider_id: 3, need_key: 'copywriting',  round: 1, price_minor: 100000, scope: 'Homepage + 4 feature pages', timeline_days: 5, status: 'OPEN' },
  { id: 4, goal_id: 1, provider_id: 3, need_key: 'copywriting',  round: 2, price_minor: 88000,  scope: 'Homepage + 4 feature pages', timeline_days: 5, status: 'SELECTED' },
  // Goal 2 — logo_design
  { id: 5, goal_id: 2, provider_id: 6, need_key: 'logo_design',  round: 1, price_minor: 25000,  scope: '3 concepts', timeline_days: 3, status: 'OPEN' },
  { id: 6, goal_id: 2, provider_id: 6, need_key: 'logo_design',  round: 2, price_minor: 17000,  scope: '3 concepts + revisions', timeline_days: 3, status: 'SELECTED' },
  // Goal 3 — copywriting
  { id: 7, goal_id: 3, provider_id: 4, need_key: 'copywriting',  round: 1, price_minor: 11000,  scope: '5 blog posts', timeline_days: 4, status: 'OPEN' },
  { id: 8, goal_id: 3, provider_id: 4, need_key: 'copywriting',  round: 2, price_minor: 10000,  scope: '5 blog posts', timeline_days: 4, status: 'SELECTED' },
  // Goal 4 — web + social
  { id: 9,  goal_id: 4, provider_id: 2, need_key: 'web_design',   round: 1, price_minor: 250000, scope: 'Landing page', timeline_days: 10, status: 'OPEN' },
  { id: 10, goal_id: 4, provider_id: 2, need_key: 'web_design',   round: 2, price_minor: 170000, scope: 'Landing page', timeline_days: 10, status: 'SELECTED' },
  { id: 11, goal_id: 4, provider_id: 7, need_key: 'social_media', round: 1, price_minor: 100000, scope: '10 graphics', timeline_days: 6, status: 'OPEN' },
  { id: 12, goal_id: 4, provider_id: 7, need_key: 'social_media', round: 2, price_minor: 77000,  scope: '10 graphics + copy', timeline_days: 6, status: 'SELECTED' },
]

// ─── Transactions ─────────────────────────────────────────────────────────────
export const mockTransactions: Transaction[] = [
  {
    id: 1, plan_id: 1, paypal_order_id: 'PP-MOCK-ORDER-7KX22109HM',
    capture_id: 'CAP-7KX22109HM9876543', amount_minor: 318000, currency: 'USD',
    status: 'COMPLETED', created_at: '2026-11-09T14:22:00Z',
  },
  {
    id: 2, plan_id: 2, paypal_order_id: 'PP-MOCK-ORDER-5XY33210JN',
    capture_id: null, amount_minor: 17000, currency: 'USD',
    status: 'CREATED', created_at: '2026-11-10T10:05:00Z',
  },
]

// ─── Scenario map (used by mockClient) ───────────────────────────────────────
export type ScenarioId = 'approved' | 'review' | 'blocked' | 'retry'

export interface ScenarioData {
  goal: Goal
  plan: Plan
  offers: Offer[]
}

export const SCENARIO_MAP: Record<number, ScenarioData> = {
  1: { goal: mockGoalApproved, plan: mockPlanApproved, offers: mockOffers.filter(o => o.goal_id === 1) },
  2: { goal: mockGoalReview,   plan: mockPlanReview,   offers: mockOffers.filter(o => o.goal_id === 2) },
  3: { goal: mockGoalBlocked,  plan: mockPlanBlocked,  offers: mockOffers.filter(o => o.goal_id === 3) },
  4: { goal: mockGoalRetry,    plan: mockPlanRetry,    offers: mockOffers.filter(o => o.goal_id === 4) },
}
