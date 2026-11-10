// src/pages/GoalDashboard.tsx (Screen 1)
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { GoalForm } from '../components/goal/GoalForm'
import { ProviderPanel } from '../components/goal/ProviderPanel'
import { useCreateGoal, useProviders } from '../api/hooks'
import { useToast } from '../components/ui/Toast'
import { ROUTES } from '../lib/constants'
import type { CreateGoalRequest } from '../api/types'

export const GoalDashboard: React.FC = () => {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const createGoal = useCreateGoal()
  const { data: providers = [], isLoading: isLoadingProviders } = useProviders()

  const handleCreateGoal = async (data: CreateGoalRequest) => {
    try {
      const goal = await createGoal.mutateAsync(data)
      showToast('Agent pipeline initialized successfully!', 'success')
      navigate(ROUTES.goal(goal.id))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to launch agent pipeline'
      showToast(msg, 'error')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">
          Procurement Command Center
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          Deploy multi-agent procurement workflows with automated provider discovery, multi-round negotiation, and PayGuard AI risk guardrails.
        </p>
      </div>

      {/* Two-column layout (60% / 40%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7">
          <GoalForm onSubmit={handleCreateGoal} isSubmitting={createGoal.isPending} />
        </div>
        <div className="lg:col-span-5">
          <ProviderPanel providers={providers} isLoading={isLoadingProviders} />
        </div>
      </div>
    </div>
  )
}
