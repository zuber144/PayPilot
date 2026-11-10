// src/mocks/mockClient.ts — realistic mock API client with progressive timeline simulation

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
  SCENARIO_MAP,
  mockGoalApproved,
  mockGoalBlocked,
  mockGoalReview,
  mockGoalRetry,
  mockOffers,
  mockPlanApproved,
  mockPlanBlocked,
  mockPlanReview,
  mockPlanRetry,
  mockProviders,
  mockTransactions,
} from './fixtures'

const delay = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms))

// In-memory state tracking
interface GoalSimulationState {
  startedAt: number
  scenarioId: number
}

const goalSimulations = new Map<number, GoalSimulationState>()
let nextGoalId = 5

// In-memory clone of plans and transactions for mutation during demo
const planStore: Record<number, Plan> = {
  1: JSON.parse(JSON.stringify(mockPlanApproved)),
  2: JSON.parse(JSON.stringify(mockPlanReview)),
  3: JSON.parse(JSON.stringify(mockPlanBlocked)),
  4: JSON.parse(JSON.stringify(mockPlanRetry)),
}

const transactionStore: Transaction[] = [...mockTransactions]

export const mockClient = {
  createGoal: async (data: CreateGoalRequest): Promise<Goal> => {
    await delay(350)
    const newId = nextGoalId++

    // Determine scenario based on prompt content or budget
    let scenarioId = 1
    const text = data.raw_text.toLowerCase()
    if (text.includes('cheapest') || text.includes('unverified') || text.includes('no matter what')) {
      scenarioId = 3 // Blocked
    } else if (text.includes('logo') || text.includes('startup') || data.budget_minor <= 20000) {
      scenarioId = 2 // Review
    } else if (text.includes('retry') || text.includes('landing page') || text.includes('social media')) {
      scenarioId = 4 // Retry
    } else {
      scenarioId = 1 // Approved
    }

    goalSimulations.set(newId, {
      startedAt: Date.now(),
      scenarioId,
    })

    const baseGoal = SCENARIO_MAP[scenarioId]?.goal ?? mockGoalApproved

    // Create a copy of the plan in store if not present
    if (!planStore[newId]) {
      const basePlan = SCENARIO_MAP[scenarioId]?.plan ?? mockPlanApproved
      planStore[newId] = {
        ...JSON.parse(JSON.stringify(basePlan)),
        id: newId,
        goal_id: newId,
      }
    }

    return {
      id: newId,
      user_id: data.user_id,
      raw_text: data.raw_text,
      parsed: baseGoal.parsed,
      budget_minor: data.budget_minor,
      currency: data.currency,
      status: 'RUNNING',
      trace: [baseGoal.trace[0]],
      created_at: new Date().toISOString(),
      plan_id: null,
    }
  },

  getGoal: async (id: number): Promise<Goal> => {
    await delay(150)
    const sim = goalSimulations.get(id)

    // For pre-seeded goals (1, 2, 3, 4) without active simulation, return full state
    if (!sim) {
      const scenario = SCENARIO_MAP[id] ?? SCENARIO_MAP[1]
      return scenario.goal
    }

    const scenario = SCENARIO_MAP[sim.scenarioId] ?? SCENARIO_MAP[1]
    const fullTrace = scenario.goal.trace

    // Progressive timeline simulation: reveal 1 event every 1200ms
    const elapsedMs = Date.now() - sim.startedAt
    const eventsToShow = Math.min(fullTrace.length, Math.floor(elapsedMs / 1200) + 1)
    const currentTrace = fullTrace.slice(0, eventsToShow)
    const isFinished = eventsToShow >= fullTrace.length

    return {
      id,
      user_id: scenario.goal.user_id,
      raw_text: scenario.goal.raw_text,
      parsed: eventsToShow >= 2 ? scenario.goal.parsed : null,
      budget_minor: scenario.goal.budget_minor,
      currency: scenario.goal.currency,
      status: isFinished ? 'PLAN_READY' : 'RUNNING',
      trace: currentTrace,
      created_at: new Date(sim.startedAt).toISOString(),
      plan_id: isFinished ? id : null,
    }
  },

  getGoalOffers: async (goalId: number): Promise<Offer[]> => {
    await delay(150)
    const sim = goalSimulations.get(goalId)
    const effectiveId = sim ? sim.scenarioId : goalId
    return mockOffers.filter((o) => o.goal_id === effectiveId)
  },

  getPlan: async (id: number): Promise<Plan> => {
    await delay(150)
    return planStore[id] ?? mockPlanApproved
  },

  runPayGuard: async (planId: number): Promise<PayGuardResult> => {
    await delay(400)
    const plan = planStore[planId] ?? mockPlanApproved
    return (plan.payguard ?? plan.payguard_result)!
  },

  approvePlan: async (planId: number, body: ApproveRequest): Promise<Plan> => {
    await delay(300)
    const plan = planStore[planId] ?? mockPlanApproved
    const updated: Plan = {
      ...plan,
      status: 'USER_APPROVED',
      approved_at: new Date().toISOString(),
    }
    planStore[planId] = updated
    // Also log acknowledged flags for verification
    if (body.acknowledged_flags.length > 0 && updated.payguard) {
      updated.payguard = {
        ...updated.payguard,
        flags: updated.payguard.flags.filter((f) => !body.acknowledged_flags.includes(f)),
      }
    }
    return updated
  },

  payPlan: async (planId: number): Promise<PayResponse> => {
    await delay(400)
    const plan = planStore[planId] ?? mockPlanApproved
    plan.status = 'PAYING'

    const orderId = `PP-MOCK-ORDER-${Math.random().toString(36).substring(2, 10).toUpperCase()}`
    const mockApprovalUrl = `/payment/return?token=${orderId}&PayerID=MOCK-PAYER-DEMO&plan_id=${planId}`

    return {
      transaction_id: transactionStore.length + 1,
      paypal_order_id: orderId,
      approval_url: mockApprovalUrl,
      status: 'CREATED',
    }
  },

  capturePayment: async (token: string, planId: number): Promise<CaptureResponse> => {
    await delay(500)
    const plan = planStore[planId] ?? mockPlanApproved
    plan.status = 'PAID'

    const captureId = `CAP-${Math.random().toString(36).substring(2, 12).toUpperCase()}`
    const newTx: Transaction = {
      id: transactionStore.length + 1,
      plan_id: planId,
      paypal_order_id: token,
      capture_id: captureId,
      amount_minor: plan.total_minor,
      currency: plan.currency,
      status: 'COMPLETED',
      created_at: new Date().toISOString(),
    }
    transactionStore.unshift(newTx)

    return {
      transaction_id: newTx.id,
      capture_id: captureId,
      amount_minor: newTx.amount_minor,
      currency: newTx.currency,
      status: 'COMPLETED',
    }
  },

  listTransactions: async (): Promise<Transaction[]> => {
    await delay(150)
    return [...transactionStore]
  },

  listProviders: async (): Promise<Provider[]> => {
    await delay(150)
    return mockProviders
  },
}
