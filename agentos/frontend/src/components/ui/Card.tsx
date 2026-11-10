// src/components/ui/Card.tsx
import React from 'react'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
}

export const Card: React.FC<CardProps> = ({
  children,
  padding = 'md',
  hover = false,
  className = '',
  ...props
}) => {
  const paddingClasses = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  }[padding]

  return (
    <div
      className={`bg-white rounded-xl border border-slate-200 shadow-sm ${
        hover ? 'hover:shadow-md transition-shadow' : ''
      } ${paddingClasses} ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
