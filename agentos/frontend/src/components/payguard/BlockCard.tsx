// src/components/payguard/BlockCard.tsx
import React, { useState } from 'react'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { useToast } from '../ui/Toast'

interface BlockCardProps {
  planId: number
  onFixApplied?: () => void
}

export const BlockCard: React.FC<BlockCardProps> = ({ planId, onFixApplied }) => {
  const { showToast } = useToast()
  const [isApplying, setIsApplying] = useState(false)

  const handleAction = (actionName: string) => {
    setIsApplying(true)
    setTimeout(() => {
      setIsApplying(false)
      showToast(`Action "${actionName}" applied for plan #${planId}`, 'success')
      if (onFixApplied) onFixApplied()
    }, 800)
  }

  return (
    <Card padding="md" className="border-red-300 bg-red-50/50 space-y-4">
      <div className="flex items-center gap-2 text-red-900">
        <span className="text-lg">🛠️</span>
        <h4 className="font-bold text-sm">One-Click Remediation Actions</h4>
      </div>

      <p className="text-xs text-red-800 leading-relaxed">
        This plan cannot be paid in its current state. Select an automated remediation path to re-run the pipeline with adjusted constraints:
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
        <Button
          variant="outline"
          size="sm"
          isLoading={isApplying}
          onClick={() => handleAction('Replace Unverified Provider')}
          className="text-xs border-red-300 text-red-800 hover:bg-red-100"
        >
          🔄 Replace Unverified Vendor
        </Button>
        <Button
          variant="outline"
          size="sm"
          isLoading={isApplying}
          onClick={() => handleAction('Request Re-negotiation')}
          className="text-xs border-red-300 text-red-800 hover:bg-red-100"
        >
          💬 Request Re-negotiation
        </Button>
        <Button
          variant="outline"
          size="sm"
          isLoading={isApplying}
          onClick={() => handleAction('Remove Non-Compliant Item')}
          className="text-xs border-red-300 text-red-800 hover:bg-red-100"
        >
          ✂️ Remove Item
        </Button>
      </div>
    </Card>
  )
}
