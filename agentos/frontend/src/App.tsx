// src/App.tsx — router wiring for all 6 routes
import { Routes, Route } from 'react-router-dom'
import { Nav } from './components/Nav'
import { HomePage } from './pages/HomePage'
import { GoalPage } from './pages/GoalPage'
import { PlanPage } from './pages/PlanPage'
import { PayPage } from './pages/PayPage'
import { PaymentReturnPage } from './pages/PaymentReturnPage'
import { TransactionsPage } from './pages/TransactionsPage'

export default function App() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/goals/:id" element={<GoalPage />} />
        <Route path="/plans/:id" element={<PlanPage />} />
        <Route path="/plans/:id/pay" element={<PayPage />} />
        <Route path="/payments/return" element={<PaymentReturnPage />} />
        <Route path="/transactions" element={<TransactionsPage />} />
      </Routes>
    </>
  )
}
