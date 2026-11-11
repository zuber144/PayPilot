// src/components/ui/Skeleton.tsx
import React from 'react'

export interface SkeletonProps {
  className?: string
  width?: string
  height?: string
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  width = 'w-full',
  height = 'h-4',
}) => {
  return (
    <div
      className={`bg-slate-200 rounded animate-pulse ${width} ${height} ${className}`}
    />
  )
}
