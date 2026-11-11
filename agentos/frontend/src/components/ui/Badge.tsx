// src/components/ui/Badge.tsx
import React from 'react'

export interface BadgeProps {
  children: React.ReactNode
  variant?: 'slate' | 'blue' | 'emerald' | 'amber' | 'red' | 'purple'
  size?: 'sm' | 'md'
  dot?: boolean
  className?: string
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'slate',
  size = 'sm',
  dot = false,
  className = '',
}) => {
  const variantMap = {
    slate: 'bg-slate-100 text-slate-700 border-slate-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-800 border-amber-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  }[variant]

  const dotColorMap = {
    slate: 'bg-slate-400',
    blue: 'bg-blue-500',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500',
    purple: 'bg-purple-500',
  }[variant]

  const sizeMap = {
    sm: 'text-xs px-2.5 py-0.5',
    md: 'text-sm px-3 py-1',
  }[size]

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${variantMap} ${sizeMap} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColorMap}`} />}
      {children}
    </span>
  )
}
