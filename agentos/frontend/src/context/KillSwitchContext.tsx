// src/context/KillSwitchContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react'

interface KillSwitchContextValue {
  paymentsEnabled: boolean
  toggleKillSwitch: () => void
  setPaymentsEnabled: (val: boolean) => void
}

const KillSwitchContext = createContext<KillSwitchContextValue>({
  paymentsEnabled: true,
  toggleKillSwitch: () => {},
  setPaymentsEnabled: () => {},
})

export const useKillSwitch = () => useContext(KillSwitchContext)

export const KillSwitchProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [paymentsEnabled, setPaymentsEnabled] = useState<boolean>(() => {
    const saved = localStorage.getItem('PAYMENTS_ENABLED')
    return saved !== null ? saved === 'true' : true
  })

  useEffect(() => {
    localStorage.setItem('PAYMENTS_ENABLED', String(paymentsEnabled))
  }, [paymentsEnabled])

  const toggleKillSwitch = () => setPaymentsEnabled((prev) => !prev)

  return (
    <KillSwitchContext.Provider value={{ paymentsEnabled, toggleKillSwitch, setPaymentsEnabled }}>
      {children}
    </KillSwitchContext.Provider>
  )
}
