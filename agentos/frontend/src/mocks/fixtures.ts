// src/mocks/fixtures.ts — fixture data for VITE_USE_MOCKS=true

import type { Goal, Offer, Plan, Provider, Transaction } from '../api/types'

export const mockProviders: Provider[] = [
  {
    id: 1, name: 'PixelCraft Studio', category: 'web_design',
    base_price_minor: 80000, min_price_minor: 55000, concession_rate: 0.15,
    rating: 4.8, turnaround_days: 10, verified: true,
    persona: 'Professional web design agency.',
  },
  {
    id: 3, name: 'WordSmith Pro', category: 'copywriting',
    base_price_minor: 30000, min_price_minor: 20000, concession_rate: 0.12,
    rating: 4.6, turnaround_days: 5, verified: true,
    persona: 'Award-winning copywriters.',
  },
]

export const mockGoal: Goal = {
  id: 1,
  user_id: 1,
  raw_text: 'Build a professional website and write compelling copy',
  parsed: { needs: ['web_design', 'copywriting'], budget_minor: 200000, currency: 'USD', deadline_days: 21 },
  budget_minor: 200000,
  currency: 'USD',
  status: 'PLANNED',
  trace: [
    { step: 'goal_analyzer', summary: 'Identified 2 needs: web_design, copywriting', duration_ms: 42, status: 'ok', used_fallback: false },
    { step: 'discovery', summary: 'Found 4 providers across 2 needs', duration_ms: 18, status: 'ok', used_fallback: false },
    { step: 'provider_agents', summary: 'Generated 4 opening offers', duration_ms: 65, status: 'ok', used_fallback: true },
    { step: 'negotiation', summary: 'Negotiated 4 offers; saved 15000 minor units total', duration_ms: 11, status: 'ok', used_fallback: false },
    { step: 'plan_generator', summary: 'Plan generated: 2 items, total 90000 USD, score=0.712', duration_ms: 24, status: 'ok', used_fallback: true },
  ],
  created_at: '2026-11-08T10:00:00Z',
  plan_id: 1,
}

export const mockOffers: Offer[] = [
  { id: 1, goal_id: 1, provider_id: 1, need_key: 'web_design', round: 2, price_minor: 68000, scope: 'Full web_design service', timeline_days: 10, status: 'SELECTED' },
  { id: 2, goal_id: 1, provider_id: 3, need_key: 'copywriting', round: 1, price_minor: 25500, scope: 'Full copywriting service', timeline_days: 5, status: 'SELECTED' },
]

export const mockPlanApproved: Plan = {
  id: 1,
  goal_id: 1,
  items: [
    { need_key: 'web_design', provider_id: 1, provider_name: 'PixelCraft Studio', price_minor: 68000, scope: 'Full web design', timeline_days: 10, offer_id: 1 },
    { need_key: 'copywriting', provider_id: 3, provider_name: 'WordSmith Pro', price_minor: 22000, scope: 'Full copywriting', timeline_days: 5, offer_id: 2 },
  ],
  total_minor: 90000,
  currency: 'USD',
  rationale: 'Selected providers offer the best balance of quality, price, and speed within your budget.',
  payguard_result: {
    verdict: 'APPROVED',
    rules: [
      { rule: 'BUDGET_CAP', passed: true, severity: 'BLOCK', reason: 'Plan total 90000 ≤ goal budget 200000' },
      { rule: 'TXN_LIMIT', passed: true, severity: 'BLOCK', reason: 'Plan total 90000 ≤ max transaction limit 1000000' },
      { rule: 'VERIFIED_PROVIDER', passed: true, severity: 'BLOCK', reason: 'All providers verified' },
      { rule: 'CURRENCY_MATCH', passed: true, severity: 'BLOCK', reason: "Currency 'USD' is valid ISO-4217" },
      { rule: 'NO_DUPLICATE', passed: true, severity: 'BLOCK', reason: 'No live transaction exists for this plan' },
      { rule: 'PRICE_FLOOR', passed: true, severity: 'BLOCK', reason: 'All item prices ≥ provider floors' },
      { rule: 'TOTAL_INTEGRITY', passed: true, severity: 'BLOCK', reason: 'Sum of items (90000) matches plan total (90000)' },
      { rule: 'AI_RISK_HIGH', passed: true, severity: 'BLOCK', reason: 'Risk score 20 < 80 (acceptable)' },
      { rule: 'AI_RISK_MEDIUM', passed: true, severity: 'REVIEW', reason: 'Risk score 20 < 50 (low risk)' },
      { rule: 'SINGLE_VENDOR_SHARE', passed: true, severity: 'REVIEW', reason: 'Max vendor share 76% ≤ 70%' },
    ],
    risk_score: 20,
    flags: [],
    summary: 'No significant risk factors detected.',
  },
  status: 'APPROVED',
  approved_at: null,
}

export const mockPlanReview: Plan = {
  id: 2,
  goal_id: 2,
  items: [
    { need_key: 'logo_design', provider_id: 6, provider_name: 'LogoRocket', price_minor: 12000, scope: 'Full logo design', timeline_days: 3, offer_id: 3 },
  ],
  total_minor: 12000,
  currency: 'USD',
  rationale: 'Only one provider fits in budget — vendor concentration risk flagged.',
  payguard_result: {
    verdict: 'REVIEW',
    rules: [
      { rule: 'BUDGET_CAP', passed: true, severity: 'BLOCK', reason: 'Plan total 12000 ≤ goal budget 20000' },
      { rule: 'SINGLE_VENDOR_SHARE', passed: false, severity: 'REVIEW', reason: 'Max vendor share 100% > 70% — concentration risk' },
      { rule: 'AI_RISK_MEDIUM', passed: false, severity: 'REVIEW', reason: 'Risk score 50 ≥ 50 — MEDIUM RISK' },
    ],
    risk_score: 50,
    flags: ['VENDOR_CONCENTRATION'],
    summary: 'Risk factors identified: VENDOR_CONCENTRATION.',
  },
  status: 'CHECKED',
  approved_at: null,
}

export const mockPlanBlocked: Plan = {
  id: 3,
  goal_id: 3,
  items: [
    { need_key: 'copywriting', provider_id: 4, provider_name: 'ContentHive', price_minor: 14000, scope: 'Full copywriting', timeline_days: 4, offer_id: 4 },
  ],
  total_minor: 14000,
  currency: 'USD',
  rationale: 'Cheapest option found, but provider is unverified.',
  payguard_result: {
    verdict: 'BLOCKED',
    rules: [
      { rule: 'VERIFIED_PROVIDER', passed: false, severity: 'BLOCK', reason: 'Unverified providers: ContentHive' },
    ],
    risk_score: 20,
    flags: [],
    summary: 'No significant AI risk factors, but policy BLOCKED due to unverified provider.',
  },
  status: 'BLOCKED',
  approved_at: null,
}

export const mockTransactions: Transaction[] = [
  {
    id: 1, plan_id: 1, paypal_order_id: 'PP-MOCK-ORDER-001',
    capture_id: null, amount_minor: 90000, currency: 'USD',
    status: 'CREATED', created_at: '2026-11-08T11:00:00Z',
  },
]
