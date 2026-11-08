// src/api/client.ts — typed API client
// Swapped for mocks when VITE_USE_MOCKS=true

import type {
  ApproveRequest,
  CaptureResponse,
  CreateGoalRequest,
  Goal,
  Offer,
  PayGuardResult,
  PayResponse,
  Plan,
  Provider,
  Transaction,
} from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const API = `${BASE}/api/v1`

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const msg = body?.error?.message ?? body?.detail ?? `HTTP ${res.status}`
    throw new Error(msg)
  }
  return res.json() as Promise<T>
}

export const realClient = {
  createGoal: (data: CreateGoalRequest) =>
    request<Goal>('/goals', { method: 'POST', body: JSON.stringify(data) }),

  getGoal: (id: number) => request<Goal>(`/goals/${id}`),

  getGoalOffers: (id: number) => request<Offer[]>(`/goals/${id}/offers`),

  getPlan: (id: number) => request<Plan>(`/plans/${id}`),

  runPayGuard: (planId: number) =>
    request<PayGuardResult>(`/plans/${planId}/payguard`, { method: 'POST' }),

  approvePlan: (planId: number, body: ApproveRequest) =>
    request<Plan>(`/plans/${planId}/approve`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  payPlan: (planId: number) =>
    request<PayResponse>(`/plans/${planId}/pay`, { method: 'POST' }),

  capturePayment: (token: string, planId: number) =>
    request<CaptureResponse>('/payments/capture', {
      method: 'POST',
      body: JSON.stringify({ token, plan_id: planId }),
    }),

  listTransactions: () => request<Transaction[]>('/payments/transactions'),

  listProviders: () => request<Provider[]>('/providers'),
}
