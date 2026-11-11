// src/api/client.ts — typed API client matching backend/app/routers
import type {
  ApproveRequest,
  CaptureResponse,
  CreateGoalRequest,
  Goal,
  GoalCreated,
  OffersOut,
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
  createGoal: async (data: CreateGoalRequest): Promise<GoalCreated> => {
    // Backend expects raw_text, budget_minor, currency, and optional scenario
    const payload: Record<string, unknown> = {
      raw_text: data.raw_text,
      budget_minor: data.budget_minor,
      currency: data.currency ?? 'USD',
    }
    if (data.scenario) {
      payload.scenario = data.scenario
    }
    return request<GoalCreated>('/goals', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  getGoal: (id: number): Promise<Goal> => request<Goal>(`/goals/${id}`),

  getGoalOffers: (id: number): Promise<OffersOut> => request<OffersOut>(`/goals/${id}/offers`),

  getPlan: (id: number): Promise<Plan> => request<Plan>(`/plans/${id}`),

  runPayGuard: (planId: number): Promise<PayGuardResult> =>
    request<PayGuardResult>(`/plans/${planId}/payguard`, { method: 'POST' }),

  approvePlan: (planId: number, body: ApproveRequest): Promise<Plan> =>
    request<Plan>(`/plans/${planId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ acknowledged_flags: body.acknowledged_flags }),
    }),

  payPlan: (planId: number): Promise<PayResponse> =>
    request<PayResponse>(`/plans/${planId}/pay`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  capturePayment: (paypalOrderId: string, _planId?: number): Promise<CaptureResponse> =>
    request<CaptureResponse>('/payments/capture', {
      method: 'POST',
      body: JSON.stringify({ paypal_order_id: paypalOrderId }),
    }),

  listTransactions: (): Promise<Transaction[]> => request<Transaction[]>('/transactions'),

  listProviders: (): Promise<Provider[]> => request<Provider[]>('/providers'),
}
