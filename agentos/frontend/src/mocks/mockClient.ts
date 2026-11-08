// src/mocks/mockClient.ts — mock implementation of the API client

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
} from '../api/types'
import {
  mockGoal,
  mockOffers,
  mockPlanApproved,
  mockPlanBlocked,
  mockPlanReview,
  mockProviders,
  mockTransactions,
} from './fixtures'

const delay = (ms = 300) => new Promise((r) => setTimeout(r, ms))

const plans: Record<number, Plan> = {
  1: { ...mockPlanApproved },
  2: { ...mockPlanReview },
  3: { ...mockPlanBlocked },
}

export const mockClient = {
  createGoal: async (_data: CreateGoalRequest): Promise<Goal> => {
    await delay(400)
    return { ...mockGoal, status: 'RUNNING' }
  },

  getGoal: async (id: number): Promise<Goal> => {
    await delay(200)
    return { ...mockGoal, id, status: 'PLANNED' }
  },

  getGoalOffers: async (_id: number): Promise<Offer[]> => {
    await delay(200)
    return mockOffers
  },

  getPlan: async (id: number): Promise<Plan> => {
    await delay(200)
    return plans[id] ?? mockPlanApproved
  },

  runPayGuard: async (planId: number): Promise<PayGuardResult> => {
    await delay(500)
    const plan = plans[planId] ?? mockPlanApproved
    return plan.payguard_result!
  },

  approvePlan: async (planId: number, _body: ApproveRequest): Promise<Plan> => {
    await delay(300)
    if (plans[planId]) {
      plans[planId] = { ...plans[planId], status: 'APPROVED' }
    }
    return plans[planId] ?? { ...mockPlanApproved, status: 'APPROVED' }
  },

  payPlan: async (planId: number): Promise<PayResponse> => {
    await delay(400)
    return {
      transaction_id: 1,
      paypal_order_id: 'PP-MOCK-ORDER-001',
      approval_url: `https://www.sandbox.paypal.com/checkoutnow?token=MOCK-${planId}`,
      status: 'CREATED',
    }
  },

  capturePayment: async (_token: string, _planId: number): Promise<CaptureResponse> => {
    await delay(600)
    return {
      transaction_id: 1,
      capture_id: 'CAP-MOCK-001',
      amount_minor: 90000,
      currency: 'USD',
      status: 'COMPLETED',
    }
  },

  listTransactions: async (): Promise<Transaction[]> => {
    await delay(200)
    return mockTransactions
  },

  listProviders: async (): Promise<Provider[]> => {
    await delay(200)
    return mockProviders
  },
}
