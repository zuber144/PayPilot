// src/lib/money.ts — all money formatting goes through here; never format in components

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  INR: '₹',
  AUD: 'A$',
  CAD: 'C$',
}

const MINOR_UNITS: Record<string, number> = {
  USD: 100,
  EUR: 100,
  GBP: 100,
  INR: 100,
  AUD: 100,
  CAD: 100,
  JPY: 1,   // yen has no minor units
}

/**
 * Format an amount stored in minor units (paise/cents) into a human string.
 * e.g. formatMinor(4100000, 'INR') => '₹41,000.00'
 *      formatMinor(90000, 'USD')   => '$900.00'
 */
export function formatMinor(amountMinor: number, currency: string): string {
  const divisor = MINOR_UNITS[currency] ?? 100
  const major = amountMinor / divisor
  const symbol = CURRENCY_SYMBOLS[currency] ?? currency + ' '
  return (
    symbol +
    major.toLocaleString('en-IN', {
      minimumFractionDigits: divisor === 1 ? 0 : 2,
      maximumFractionDigits: divisor === 1 ? 0 : 2,
    })
  )
}

/** Legacy alias used by older components */
export function formatMoney(amountMinor: number, currency = 'USD'): string {
  return formatMinor(amountMinor, currency)
}
