// src/components/trace/RetryChip.tsx
import React from 'react'

interface RetryChipProps {
  count?: number
}

export const RetryChip: React.FC<RetryChipProps> = ({ count = 1 }) => {
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-300">
      <span>↺</span>
      <span>Retry #{count}</span>
    </span>
  )
}
