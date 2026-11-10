// src/components/ui/Spinner.tsx
import React from 'react'

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  color?: 'current' | 'primary' | 'white'
  className?: string
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  color = 'primary',
  className = '',
}) => {
  const sizeMap = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3',
  }[size]

  const colorMap = {
    current: 'border-current border-t-transparent',
    primary: 'border-paypal-500 border-t-transparent',
    white: 'border-white border-t-transparent',
  }[color]

  return (
    <div
      role="status"
      aria-label="Loading"
      className={`inline-block rounded-full animate-spin ${sizeMap} ${colorMap} ${className}`}
    />
  )
}
