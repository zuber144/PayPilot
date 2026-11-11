// src/App.tsx — routing with AppShell, KillSwitchProvider, and ToastProvider
import { Routes, Route } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { KillSwitchProvider } from './context/KillSwitchContext'
import { ToastProvider } from './components/ui/Toast'

// Screen pages
import { GoalDashboard } from './pages/GoalDashboard'
import { GoalExecution } from './pages/GoalExecution'
import { PlanPage } from './pages/PlanPage'
import { PaymentPage } from './pages/PaymentPage'
import { PaymentReturn } from './pages/PaymentReturn'
import { Transactions } from './pages/Transactions'
import { NotFound } from './pages/NotFound'

export default function App() {
  return (
    <KillSwitchProvider>
      <ToastProvider>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<GoalDashboard />} />
            <Route path="/goals/:id" element={<GoalExecution />} />
            <Route path="/plans/:id" element={<PlanPage />} />
            <Route path="/plans/:id/pay" element={<PaymentPage />} />
            <Route path="/payment/return" element={<PaymentReturn />} />
            <Route path="/payments/return" element={<PaymentReturn />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </ToastProvider>
    </KillSwitchProvider>
  )
}
