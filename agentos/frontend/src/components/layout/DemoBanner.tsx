// src/components/layout/DemoBanner.tsx
import React from 'react'
import { useKillSwitch } from '../../context/KillSwitchContext'

export const DemoBanner: React.FC = () => {
  const { paymentsEnabled, toggleKillSwitch } = useKillSwitch()

  return (
    <div className="bg-amber-100 border-b border-amber-200 px-4 py-2 text-xs sm:text-sm text-amber-900 flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center gap-2">
        <span className="font-semibold px-1.5 py-0.5 rounded bg-amber-200 text-amber-950 uppercase text-[10px] tracking-wide">
          Demo Mode
        </span>
        <span>
          Seeded providers &amp; PayPal Sandbox only. <strong>No real money moves.</strong>
        </span>
      </div>
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 cursor-pointer select-none text-xs">
          <input
            type="checkbox"
            checked={paymentsEnabled}
            onChange={toggleKillSwitch}
            className="rounded border-amber-400 text-paypal-500 focus:ring-paypal-500 h-3.5 w-3.5"
          />
          <span className="font-medium">
            Kill Switch:{' '}
            <span className={paymentsEnabled ? 'text-emerald-700 font-bold' : 'text-red-700 font-bold'}>
              {paymentsEnabled ? 'PAYMENTS ARMED' : 'DISABLED'}
            </span>
          </span>
        </label>
      </div>
    </div>
  )
}
