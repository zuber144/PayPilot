// src/mocks/fixtures.ts — rich fixture data for all 4 demo scenarios
// Matching backend/seed.py and backend/app/schemas.py

import type {
  Goal,
  OffersOut,
  Plan,
  Provider,
  Transaction,
  TraceEvent,
  PayGuardRuleResult,
  Flag,
} from '../api/types'

// ─── 6 Seeded Providers (from backend/seed.py) ────────────────────────────────
export const mockProviders: Provider[] = [
  {
    id: 1,
    name: 'ABC Catering',
    category: 'catering',
    base_price_minor: 2800000,
    min_price_minor: 2400000,
    concession_rate: 0.0375,
    rating: 4.6,
    turnaround_days: 7,
    verified: true,
    currency: 'USD',
    persona: 'Trusted corporate and event caterer with full-service buffet setups.',
    demo: true,
  },
  {
    id: 2,
    name: 'Spice Route Caterers',
    category: 'catering',
    base_price_minor: 3200000,
    min_price_minor: 2700000,
    concession_rate: 0.04,
    rating: 4.4,
    turnaround_days: 6,
    verified: true,
    currency: 'USD',
    persona: 'Premium regional Indian cuisine specialist with live stations.',
    demo: true,
  },
  {
    id: 3,
    name: 'QuickBites Co',
    category: 'catering',
    base_price_minor: 2200000,
    min_price_minor: 2000000,
    concession_rate: 0.04,
    rating: 4.1,
    turnaround_days: 5,
    verified: false,
    currency: 'USD',
    persona: 'Low-cost express event caterer for casual parties.',
    demo: true,
  },
  {
    id: 4,
    name: 'Studio X',
    category: 'photography',
    base_price_minor: 1800000,
    min_price_minor: 1500000,
    concession_rate: 0.0385,
    rating: 4.7,
    turnaround_days: 4,
    verified: true,
    currency: 'USD',
    persona: 'Award-winning event photography studio with rapid 4-day delivery.',
    demo: true,
  },
  {
    id: 5,
    name: 'LensCraft',
    category: 'photography',
    base_price_minor: 2100000,
    min_price_minor: 1750000,
    concession_rate: 0.04,
    rating: 4.2,
    turnaround_days: 9,
    verified: true,
    currency: 'USD',
    persona: 'Candid and documentary event photographers with full gallery delivery.',
    demo: true,
  },
  {
    id: 6,
    name: 'PixelNest',
    category: 'photography',
    base_price_minor: 1400000,
    min_price_minor: 1200000,
    concession_rate: 0.05,
    rating: 4.5,
    turnaround_days: 3,
    verified: false,
    currency: 'USD',
    persona: 'Freelance rapid-turnaround photo crew for compact events.',
    demo: true,
  },
]

// ─── Scenario 1: Clean Approval (Goal 1) ──────────────────────────────────────
const traceClean: TraceEvent[] = [
  { seq: 1, ts: '2026-11-10T12:00:00Z', node: 'goal', action: 'parse_goal', summary: 'Parsed 2 need(s): catering, photography', duration_ms: 2, status: 'OK' },
  { seq: 2, ts: '2026-11-10T12:00:01Z', node: 'discovery', action: 'discover', summary: 'Discovered 4 candidate(s) for 2 need(s)', duration_ms: 3, status: 'OK' },
  { seq: 3, ts: '2026-11-10T12:00:02Z', node: 'provider', action: 'initial_offers', summary: 'Obtained initial quotes from 4 providers', duration_ms: 4, status: 'OK' },
  { seq: 4, ts: '2026-11-10T12:00:03Z', node: 'negotiation', action: 'negotiate', summary: 'Negotiation round 1 complete: 4 counter-offer(s)', duration_ms: 5, status: 'OK' },
  { seq: 5, ts: '2026-11-10T12:00:04Z', node: 'negotiation', action: 'negotiate', summary: 'Negotiation round 2 complete: saved $3,033.34 total', duration_ms: 4, status: 'OK' },
  { seq: 6, ts: '2026-11-10T12:00:05Z', node: 'planning', action: 'generate_plan', summary: 'Optimal plan synthesized: 2 item(s), total $40,966.66', duration_ms: 3, status: 'OK' },
  { seq: 7, ts: '2026-11-10T12:00:06Z', node: 'payguard', action: 'evaluate', summary: 'PayGuard evaluated: all 10 rules PASS — APPROVED', duration_ms: 2, status: 'OK' },
]

const rulesClean: PayGuardRuleResult[] = [
  { id: 'BUDGET_CAP', result: 'PASS', detail: 'Plan total $40,966.66 <= goal budget $50,000.00' },
  { id: 'TXN_LIMIT', result: 'PASS', detail: 'Plan total $40,966.66 <= max limit $100,000.00' },
  { id: 'VERIFIED_PROVIDER', result: 'PASS', detail: 'All selected providers (ABC Catering, Studio X) are verified' },
  { id: 'CURRENCY_MATCH', result: 'PASS', detail: "Currency 'USD' matches goal currency 'USD'" },
  { id: 'NO_DUPLICATE', result: 'PASS', detail: 'No existing active transaction exists for this plan' },
  { id: 'PRICE_FLOOR', result: 'PASS', detail: 'All item prices >= provider minimum price floors' },
  { id: 'TOTAL_INTEGRITY', result: 'PASS', detail: 'Item sum (4,096,666 cents) exactly matches plan total (4,096,666 cents)' },
  { id: 'AI_RISK_HIGH', result: 'PASS', detail: 'AI risk score 0.10 < 0.70 high threshold' },
  { id: 'AI_RISK_MEDIUM', result: 'PASS', detail: 'AI risk score 0.10 < 0.40 medium threshold' },
  { id: 'SINGLE_VENDOR_SHARE', result: 'PASS', detail: 'Max single vendor share is 60.9% <= 70.0% threshold' },
]

export const mockGoalClean: Goal = {
  id: 1,
  status: 'PLAN_READY',
  raw_text: 'Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days',
  budget_minor: 5000000,
  currency: 'USD',
  scenario: 'clean',
  parsed: {
    needs: [
      { key: 'catering', category: 'catering', quantity: 100, must_haves: [] },
      { key: 'photography', category: 'photography', quantity: 1, must_haves: [] },
    ],
    deadline_days: 10,
    currency: 'USD',
  },
  question: null,
  trace: traceClean,
  plan_id: 1,
  created_at: '2026-11-10T12:00:00Z',
}

export const mockPlanClean: Plan = {
  id: 1,
  goal_id: 1,
  status: 'CHECKED',
  currency: 'USD',
  total_minor: 4096666,
  budget_minor: 5000000,
  rationale: 'Selected the lowest-total combination of verified providers within budget: ABC Catering ($24,966.66) and Studio X ($16,000.00). Both meet the 10-day timeline requirement.',
  items: [
    { need_key: 'catering', provider_id: 1, provider_name: 'ABC Catering', price_minor: 2496666, timeline_days: 7, verified: true, currency: 'USD' },
    { need_key: 'photography', provider_id: 4, provider_name: 'Studio X', price_minor: 1600000, timeline_days: 4, verified: true, currency: 'USD' },
  ],
  payguard: {
    verdict: 'APPROVED',
    risk_score: 0.10,
    ai_ok: true,
    flags: [],
    rules: rulesClean,
  },
  acknowledged_flags: [],
  approved_at: null,
}

// ─── Scenario 2: Retry Scenario (Goal 2) ──────────────────────────────────────
const traceRetry: TraceEvent[] = [
  { seq: 1, ts: '2026-11-10T12:05:00Z', node: 'goal', action: 'parse_goal', summary: 'Parsed 2 need(s): catering, photography', duration_ms: 2, status: 'OK' },
  { seq: 2, ts: '2026-11-10T12:05:01Z', node: 'discovery', action: 'discover', summary: 'Initial strict filters yielded insufficient coverage for photography', duration_ms: 3, status: 'RETRY', retry_count: 1 },
  { seq: 3, ts: '2026-11-10T12:05:02Z', node: 'discovery', action: 'retry_discovery', summary: 'Relaxed turnaround filter: LensCraft discovered, coverage sufficient', duration_ms: 3, status: 'OK' },
  { seq: 4, ts: '2026-11-10T12:05:03Z', node: 'negotiation', action: 'negotiate', summary: 'Negotiated 3 rounds across candidates', duration_ms: 5, status: 'OK' },
  { seq: 5, ts: '2026-11-10T12:05:04Z', node: 'planning', action: 'generate_plan', summary: 'Synthesized plan: 2 items, total $42,466.66', duration_ms: 3, status: 'OK' },
  { seq: 6, ts: '2026-11-10T12:05:05Z', node: 'payguard', action: 'evaluate', summary: 'All 10 rules PASS — APPROVED', duration_ms: 2, status: 'OK' },
]

export const mockGoalRetry: Goal = {
  id: 2,
  status: 'PLAN_READY',
  raw_text: 'Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days',
  budget_minor: 5000000,
  currency: 'USD',
  scenario: 'retry',
  parsed: {
    needs: [
      { key: 'catering', category: 'catering', quantity: 100, must_haves: [] },
      { key: 'photography', category: 'photography', quantity: 1, must_haves: [] },
    ],
    deadline_days: 10,
    currency: 'USD',
  },
  question: null,
  trace: traceRetry,
  plan_id: 2,
  created_at: '2026-11-10T12:05:00Z',
}

export const mockPlanRetry: Plan = {
  id: 2,
  goal_id: 2,
  status: 'CHECKED',
  currency: 'USD',
  total_minor: 4246666,
  budget_minor: 5000000,
  rationale: 'Initial strict filters relaxed preference constraints (verification was preserved). ABC Catering and LensCraft selected within budget.',
  items: [
    { need_key: 'catering', provider_id: 1, provider_name: 'ABC Catering', price_minor: 2496666, timeline_days: 7, verified: true, currency: 'USD' },
    { need_key: 'photography', provider_id: 5, provider_name: 'LensCraft', price_minor: 1750000, timeline_days: 9, verified: true, currency: 'USD' },
  ],
  payguard: {
    verdict: 'APPROVED',
    risk_score: 0.15,
    ai_ok: true,
    flags: [],
    rules: rulesClean,
  },
  acknowledged_flags: [],
  approved_at: null,
}

// ─── Scenario 3: Blocked Scenario (Goal 3) ────────────────────────────────────
const traceBlocked: TraceEvent[] = [
  { seq: 1, ts: '2026-11-10T12:10:00Z', node: 'goal', action: 'parse_goal', summary: 'Parsed 2 need(s): catering, photography', duration_ms: 2, status: 'OK' },
  { seq: 2, ts: '2026-11-10T12:10:01Z', node: 'discovery', action: 'discover', summary: 'Low budget $36,000 forced inclusion of unverified candidates', duration_ms: 3, status: 'OK' },
  { seq: 3, ts: '2026-11-10T12:10:02Z', node: 'negotiation', action: 'negotiate', summary: 'Concluded round 2 for QuickBites Co & PixelNest', duration_ms: 4, status: 'OK' },
  { seq: 4, ts: '2026-11-10T12:10:03Z', node: 'planning', action: 'generate_plan', summary: 'Plan generated with unverified provider QuickBites Co', duration_ms: 3, status: 'OK' },
  { seq: 5, ts: '2026-11-10T12:10:04Z', node: 'payguard', action: 'evaluate', summary: 'Rule VERIFIED_PROVIDER failed: BLOCK verdict triggered', duration_ms: 2, status: 'ERROR' },
]

const rulesBlocked: PayGuardRuleResult[] = [
  { id: 'BUDGET_CAP', result: 'PASS', detail: 'Plan total $32,000.00 <= goal budget $36,000.00' },
  { id: 'TXN_LIMIT', result: 'PASS', detail: 'Plan total $32,000.00 <= max limit $100,000.00' },
  { id: 'VERIFIED_PROVIDER', result: 'BLOCK', detail: 'Provider QuickBites Co is NOT verified — settlement strictly prohibited' },
  { id: 'CURRENCY_MATCH', result: 'PASS', detail: "Currency 'USD' matches goal currency" },
  { id: 'NO_DUPLICATE', result: 'PASS', detail: 'No existing transaction exists' },
  { id: 'PRICE_FLOOR', result: 'PASS', detail: 'Prices exceed minimum floors' },
  { id: 'TOTAL_INTEGRITY', result: 'PASS', detail: 'Item sum matches total' },
  { id: 'AI_RISK_HIGH', result: 'PASS', detail: 'AI risk score 0.20 < 0.70' },
  { id: 'AI_RISK_MEDIUM', result: 'PASS', detail: 'AI risk score 0.20 < 0.40' },
  { id: 'SINGLE_VENDOR_SHARE', result: 'PASS', detail: 'Vendor share 62.5% <= 70%' },
]

export const mockGoalBlocked: Goal = {
  id: 3,
  status: 'PLAN_READY',
  raw_text: 'Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days',
  budget_minor: 3600000,
  currency: 'USD',
  scenario: 'blocked',
  parsed: {
    needs: [
      { key: 'catering', category: 'catering', quantity: 100, must_haves: [] },
      { key: 'photography', category: 'photography', quantity: 1, must_haves: [] },
    ],
    deadline_days: 10,
    currency: 'USD',
  },
  question: null,
  trace: traceBlocked,
  plan_id: 3,
  created_at: '2026-11-10T12:10:00Z',
}

export const mockPlanBlocked: Plan = {
  id: 3,
  goal_id: 3,
  status: 'CHECKED',
  currency: 'USD',
  total_minor: 3200000,
  budget_minor: 3600000,
  rationale: 'Lowest-cost providers fit within the reduced budget, but QuickBites Co fails the verified provider security check.',
  items: [
    { need_key: 'catering', provider_id: 3, provider_name: 'QuickBites Co', price_minor: 2000000, timeline_days: 5, verified: false, currency: 'USD' },
    { need_key: 'photography', provider_id: 6, provider_name: 'PixelNest', price_minor: 1200000, timeline_days: 3, verified: false, currency: 'USD' },
  ],
  payguard: {
    verdict: 'BLOCKED',
    risk_score: 0.20,
    ai_ok: true,
    flags: [
      { id: 'VERIFIED_PROVIDER', source: 'POLICY', message: 'Provider QuickBites Co is NOT verified', requires_ack: false },
    ],
    rules: rulesBlocked,
  },
  acknowledged_flags: [],
  approved_at: null,
}

// ─── Scenario 4: Review Scenario (Goal 4) ────────────────────────────────────
const traceReview: TraceEvent[] = [
  { seq: 1, ts: '2026-11-10T12:15:00Z', node: 'goal', action: 'parse_goal', summary: 'Parsed 1 need: catering', duration_ms: 2, status: 'OK' },
  { seq: 2, ts: '2026-11-10T12:15:01Z', node: 'discovery', action: 'discover', summary: 'Found 3 catering providers', duration_ms: 3, status: 'OK' },
  { seq: 3, ts: '2026-11-10T12:15:02Z', node: 'negotiation', action: 'negotiate', summary: 'Negotiated 3 rounds with ABC Catering', duration_ms: 4, status: 'OK' },
  { seq: 4, ts: '2026-11-10T12:15:03Z', node: 'planning', action: 'generate_plan', summary: 'Synthesized single-vendor plan: $24,966.66', duration_ms: 2, status: 'OK' },
  { seq: 5, ts: '2026-11-10T12:15:04Z', node: 'payguard', action: 'evaluate', summary: 'SINGLE_VENDOR_SHARE rule triggered REVIEW verdict', duration_ms: 2, status: 'OK' },
]

const flagsReview: Flag[] = [
  {
    id: 'SINGLE_VENDOR_SHARE',
    source: 'POLICY',
    message: 'Single vendor (ABC Catering) accounts for 100.0% of plan total (exceeds 70.0% threshold)',
    requires_ack: true,
  },
]

const rulesReview: PayGuardRuleResult[] = [
  { id: 'BUDGET_CAP', result: 'PASS', detail: 'Plan total $24,966.66 <= goal budget $50,000.00' },
  { id: 'TXN_LIMIT', result: 'PASS', detail: 'Plan total $24,966.66 <= max limit $100,000.00' },
  { id: 'VERIFIED_PROVIDER', result: 'PASS', detail: 'ABC Catering is verified' },
  { id: 'CURRENCY_MATCH', result: 'PASS', detail: "Currency 'USD' matches goal" },
  { id: 'NO_DUPLICATE', result: 'PASS', detail: 'No duplicate transaction' },
  { id: 'PRICE_FLOOR', result: 'PASS', detail: 'Price $24,966.66 >= floor $24,000.00' },
  { id: 'TOTAL_INTEGRITY', result: 'PASS', detail: 'Sum matches total' },
  { id: 'AI_RISK_HIGH', result: 'PASS', detail: 'AI risk score 0.10 < 0.70' },
  { id: 'AI_RISK_MEDIUM', result: 'PASS', detail: 'AI risk score 0.10 < 0.40' },
  { id: 'SINGLE_VENDOR_SHARE', result: 'REVIEW', detail: 'Single vendor accounts for 100.0% of plan total (threshold 70.0%)' },
]

export const mockGoalReview: Goal = {
  id: 4,
  status: 'PLAN_READY',
  raw_text: 'Catering for 100 people for our office event in 10 days',
  budget_minor: 5000000,
  currency: 'USD',
  scenario: 'review',
  parsed: {
    needs: [
      { key: 'catering', category: 'catering', quantity: 100, must_haves: [] },
    ],
    deadline_days: 10,
    currency: 'USD',
  },
  question: null,
  trace: traceReview,
  plan_id: 4,
  created_at: '2026-11-10T12:15:00Z',
}

export const mockPlanReview: Plan = {
  id: 4,
  goal_id: 4,
  status: 'CHECKED',
  currency: 'USD',
  total_minor: 2496666,
  budget_minor: 5000000,
  rationale: 'ABC Catering selected as the single caterer for 100 guests. Concentration risk flagged for human acknowledgment.',
  items: [
    { need_key: 'catering', provider_id: 1, provider_name: 'ABC Catering', price_minor: 2496666, timeline_days: 7, verified: true, currency: 'USD' },
  ],
  payguard: {
    verdict: 'REVIEW',
    risk_score: 0.10,
    ai_ok: true,
    flags: flagsReview,
    rules: rulesReview,
  },
  acknowledged_flags: [],
  approved_at: null,
}

// ─── Grouped Offers (matching backend OffersOut) ──────────────────────────────
export const mockOffersOut: OffersOut = {
  goal_id: 1,
  groups: [
    {
      need_key: 'catering',
      offers: [
        {
          provider_id: 1,
          provider_name: 'ABC Catering',
          verified: true,
          rating: 4.6,
          timeline_days: 7,
          opening_price_minor: 2800000,
          final_price_minor: 2496666,
          status: 'SELECTED',
          rounds: [
            { round: 0, price_minor: 2800000, counter_minor: null, status: 'OPEN', scope: 'Full buffet catering for 100' },
            { round: 1, price_minor: 2695000, counter_minor: 2520000, status: 'COUNTERED', scope: 'Full buffet catering for 100' },
            { round: 2, price_minor: 2593938, counter_minor: 2425500, status: 'COUNTERED', scope: 'Full buffet catering for 100' },
            { round: 3, price_minor: 2496666, counter_minor: 2334544, status: 'SELECTED', scope: 'Full buffet catering for 100' },
          ],
        },
        {
          provider_id: 2,
          provider_name: 'Spice Route Caterers',
          verified: true,
          rating: 4.4,
          timeline_days: 6,
          opening_price_minor: 3200000,
          final_price_minor: 2838144,
          status: 'ACCEPTED',
          rounds: [
            { round: 0, price_minor: 3200000, counter_minor: null, status: 'OPEN', scope: 'Regional Indian buffet' },
            { round: 1, price_minor: 3072000, counter_minor: 2880000, status: 'COUNTERED', scope: 'Regional Indian buffet' },
            { round: 2, price_minor: 2949120, counter_minor: 2764800, status: 'COUNTERED', scope: 'Regional Indian buffet' },
            { round: 3, price_minor: 2838144, counter_minor: 2700000, status: 'ACCEPTED', scope: 'Regional Indian buffet' },
          ],
        },
      ],
    },
    {
      need_key: 'photography',
      offers: [
        {
          provider_id: 4,
          provider_name: 'Studio X',
          verified: true,
          rating: 4.7,
          timeline_days: 4,
          opening_price_minor: 1800000,
          final_price_minor: 1600000,
          status: 'SELECTED',
          rounds: [
            { round: 0, price_minor: 1800000, counter_minor: null, status: 'OPEN', scope: 'Full-day event coverage & gallery' },
            { round: 1, price_minor: 1730700, counter_minor: 1620000, status: 'COUNTERED', scope: 'Full-day event coverage & gallery' },
            { round: 2, price_minor: 1664068, counter_minor: 1557630, status: 'COUNTERED', scope: 'Full-day event coverage & gallery' },
            { round: 3, price_minor: 1600000, counter_minor: 1500000, status: 'SELECTED', scope: 'Full-day event coverage & gallery' },
          ],
        },
        {
          provider_id: 5,
          provider_name: 'LensCraft',
          verified: true,
          rating: 4.2,
          timeline_days: 9,
          opening_price_minor: 2100000,
          final_price_minor: 1862528,
          status: 'ACCEPTED',
          rounds: [
            { round: 0, price_minor: 2100000, counter_minor: null, status: 'OPEN', scope: 'Candid event documentary' },
            { round: 1, price_minor: 2016000, counter_minor: 1890000, status: 'COUNTERED', scope: 'Candid event documentary' },
            { round: 2, price_minor: 1935360, counter_minor: 1814400, status: 'COUNTERED', scope: 'Candid event documentary' },
            { round: 3, price_minor: 1862528, counter_minor: 1750000, status: 'ACCEPTED', scope: 'Candid event documentary' },
          ],
        },
      ],
    },
  ],
}

// ─── Transactions ─────────────────────────────────────────────────────────────
export const mockTransactions: Transaction[] = [
  {
    id: 1,
    plan_id: 1,
    goal_id: 1,
    goal_summary: 'Corporate event in Bangalore: catering for 100 people and a photographer',
    paypal_order_id: 'MOCK-plan-1',
    capture_id: 'MOCK-CAP-MOCK-plan-1',
    amount_minor: 4096666,
    currency: 'USD',
    status: 'COMPLETED',
    created_at: '2026-11-10T12:00:02Z',
  },
]

export const SCENARIO_MAP: Record<number, { goal: Goal; plan: Plan; offers: OffersOut }> = {
  1: { goal: mockGoalClean, plan: mockPlanClean, offers: mockOffersOut },
  2: { goal: mockGoalRetry, plan: mockPlanRetry, offers: mockOffersOut },
  3: { goal: mockGoalBlocked, plan: mockPlanBlocked, offers: mockOffersOut },
  4: { goal: mockGoalReview, plan: mockPlanReview, offers: mockOffersOut },
}
