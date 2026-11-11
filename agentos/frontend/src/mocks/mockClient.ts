// src/mocks/mockClient.ts — realistic mock API client matching backend/app/schemas.py

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
} from '../api/types'
import {
  SCENARIO_MAP,
  mockGoalClean,
  mockGoalRetry,
  mockGoalBlocked,
  mockGoalReview,
  mockOffersOut,
  mockPlanClean,
  mockPlanRetry,
  mockPlanBlocked,
  mockPlanReview,
  mockProviders,
  mockTransactions,
} from './fixtures'

const delay = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms))

interface GoalSimulationState {
  startedAt: number
  scenarioId: number
}

const goalSimulations = new Map<number, GoalSimulationState>()
let nextGoalId = 5

const planStore: Record<number, Plan> = {
  1: JSON.parse(JSON.stringify(mockPlanClean)),
  2: JSON.parse(JSON.stringify(mockPlanRetry)),
  3: JSON.parse(JSON.stringify(mockPlanBlocked)),
  4: JSON.parse(JSON.stringify(mockPlanReview)),
}

const transactionStore: Transaction[] = [...mockTransactions]

export const mockClient = {
  createGoal: async (data: CreateGoalRequest): Promise<GoalCreated> => {
    await delay(350)
    const newId = nextGoalId++

    // Determine scenario based on scenario key, text content, or budget
    let scenarioId = 1
    if (data.scenario === 'blocked') {
      scenarioId = 3
    } else if (data.scenario === 'retry') {
      scenarioId = 2
    } else if (data.scenario === 'review') {
      scenarioId = 4
    } else if (data.scenario === 'clean') {
      scenarioId = 1
    } else {
      const text = data.raw_text.toLowerCase()
      if (text.includes('cheapest') || text.includes('unverified') || data.budget_minor < 4000000) {
        scenarioId = 3
      } else if (text.includes('single') || text.includes('only') || !text.includes('photograph')) {
        scenarioId = 4
      } else if (text.includes('retry') || text.includes('strict')) {
        scenarioId = 2
      } else {
        scenarioId = 1
      }
    }

    goalSimulations.set(newId, {
      startedAt: Date.now(),
      scenarioId,
    })

    if (!planStore[newId]) {
      const basePlan = SCENARIO_MAP[scenarioId]?.plan ?? mockPlanClean
      planStore[newId] = {
        ...JSON.parse(JSON.stringify(basePlan)),
        id: newId,
        goal_id: newId,
      }
    }

    return {
      id: newId,
      status: 'RUNNING',
    }
  },

  getGoal: async (id: number): Promise<Goal> => {
    await delay(150)
    const sim = goalSimulations.get(id)

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
      status: isFinished ? 'PLAN_READY' : 'RUNNING',
      raw_text: scenario.goal.raw_text,
      budget_minor: scenario.goal.budget_minor,
      currency: scenario.goal.currency,
      scenario: scenario.goal.scenario,
      parsed: eventsToShow >= 2 ? scenario.goal.parsed : null,
      question: scenario.goal.question,
      trace: currentTrace,
      created_at: new Date(sim.startedAt).toISOString(),
      plan_id: isFinished ? id : null,
    }
  },

  getGoalOffers: async (goalId: number): Promise<OffersOut> => {
    await delay(150)
    return mockOffersOut
  },

  getPlan: async (id: number): Promise<Plan> => {
    await delay(150)
    return planStore[id] ?? mockPlanClean
  },

  runPayGuard: async (planId: number): Promise<PayGuardResult> => {
    await delay(400)
    const plan = planStore[planId] ?? mockPlanClean
    return (plan.payguard ?? plan.payguard_result)!
  },

  approvePlan: async (planId: number, body: ApproveRequest): Promise<Plan> => {
    await delay(300)
    const plan = planStore[planId] ?? mockPlanClean
    const updated: Plan = {
      ...plan,
      status: 'USER_APPROVED',
      approved_at: new Date().toISOString(),
      acknowledged_flags: body.acknowledged_flags,
    }
    planStore[planId] = updated
    return updated
  },

  payPlan: async (planId: number): Promise<PayResponse> => {
    await delay(400)
    const plan = planStore[planId] ?? mockPlanClean
    plan.status = 'PAYING'

    const orderId = `MOCK-plan-${planId}`
    const mockApprovalUrl = `/payments/return?token=${orderId}&PayerID=MOCK-PAYER-DEMO&plan_id=${planId}`

    return {
      plan_id: planId,
      paypal_order_id: orderId,
      approval_url: mockApprovalUrl,
      status: 'PAYING',
      reused: false,
    }
  },

  capturePayment: async (paypalOrderId: string, planId?: number): Promise<CaptureResponse> => {
    await delay(500)
    const effectivePlanId = planId ?? 1
    const plan = planStore[effectivePlanId] ?? mockPlanClean
    plan.status = 'PAID'

    const captureId = `MOCK-CAP-${paypalOrderId}`
    const newTx: Transaction = {
      id: transactionStore.length + 1,
      plan_id: effectivePlanId,
      goal_id: plan.goal_id,
      goal_summary: 'Corporate event in Bangalore',
      paypal_order_id: paypalOrderId,
      capture_id: captureId,
      amount_minor: plan.total_minor,
      currency: plan.currency,
      status: 'COMPLETED',
      created_at: new Date().toISOString(),
    }
    transactionStore.unshift(newTx)

    return {
      id: newTx.id,
      transaction_id: newTx.id,
      capture_id: captureId,
      paypal_order_id: paypalOrderId,
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
