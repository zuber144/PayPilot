// src/api/hooks.ts — typed TanStack Query hooks for all domain operations

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './index'
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

// ─── Goal Hooks ───────────────────────────────────────────────────────────────
export function useCreateGoal() {
  const queryClient = useQueryClient()
  return useMutation<Goal, Error, CreateGoalRequest>({
    mutationFn: (data) => api.createGoal(data),
    onSuccess: (goal) => {
      queryClient.setQueryData(['goal', goal.id], goal)
    },
  })
}

export function useGoal(id: number | null | undefined, options?: { poll?: boolean }) {
  return useQuery<Goal, Error>({
    queryKey: ['goal', id],
    queryFn: () => {
      if (!id) throw new Error('Goal ID is required')
      return api.getGoal(id)
    },
    enabled: Boolean(id),
    refetchInterval: (query) => {
      if (!options?.poll) return false
      const goal = query.state.data
      if (!goal) return 1200
      // Continue polling while RUNNING or status is not terminal
      if (goal.status === 'RUNNING') return 1200
      return false
    },
  })
}

export function useGoalOffers(goalId: number | null | undefined) {
  return useQuery<Offer[], Error>({
    queryKey: ['offers', goalId],
    queryFn: () => {
      if (!goalId) return []
      return api.getGoalOffers(goalId)
    },
    enabled: Boolean(goalId),
  })
}

// ─── Plan Hooks ───────────────────────────────────────────────────────────────
export function usePlan(id: number | null | undefined) {
  return useQuery<Plan, Error>({
    queryKey: ['plan', id],
    queryFn: () => {
      if (!id) throw new Error('Plan ID is required')
      return api.getPlan(id)
    },
    enabled: Boolean(id),
  })
}

export function usePayGuard(planId: number | null | undefined) {
  const queryClient = useQueryClient()
  return useMutation<PayGuardResult, Error, void>({
    mutationFn: () => {
      if (!planId) throw new Error('Plan ID is required')
      return api.runPayGuard(planId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan', planId] })
    },
  })
}

export function useApprovePlan(planId: number | null | undefined) {
  const queryClient = useQueryClient()
  return useMutation<Plan, Error, ApproveRequest>({
    mutationFn: (body) => {
      if (!planId) throw new Error('Plan ID is required')
      return api.approvePlan(planId, body)
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['plan', planId], updated)
    },
  })
}

export function usePayPlan(planId: number | null | undefined) {
  return useMutation<PayResponse, Error, void>({
    mutationFn: () => {
      if (!planId) throw new Error('Plan ID is required')
      return api.payPlan(planId)
    },
  })
}

export function useCapturePayment() {
  const queryClient = useQueryClient()
  return useMutation<CaptureResponse, Error, { token: string; planId: number }>({
    mutationFn: ({ token, planId }) => api.capturePayment(token, planId),
    onSuccess: (_res, variables) => {
      queryClient.invalidateQueries({ queryKey: ['plan', variables.planId] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

// ─── Providers & Transactions ─────────────────────────────────────────────────
export function useProviders() {
  return useQuery<Provider[], Error>({
    queryKey: ['providers'],
    queryFn: () => api.listProviders(),
    staleTime: 60_000,
  })
}

export function useTransactions() {
  return useQuery<Transaction[], Error>({
    queryKey: ['transactions'],
    queryFn: () => api.listTransactions(),
  })
}
