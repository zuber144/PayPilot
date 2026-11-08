// src/components/Money.tsx — formats minor units to a human-readable string
// NEVER do money arithmetic in components — always use this helper

/**
 * Convert minor units (cents) to a formatted decimal string.
 * E.g. formatMoney(90000, 'USD') → '$900.00'
 */
export function formatMoney(minorUnits: number, currency: string): string {
  const value = minorUnits / 100
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
    }).format(value)
  } catch {
    return `${currency} ${value.toFixed(2)}`
  }
}

interface MoneyProps {
  minor: number
  currency: string
  className?: string
}

export function Money({ minor, currency, className }: MoneyProps) {
  return <span className={className}>{formatMoney(minor, currency)}</span>
}
