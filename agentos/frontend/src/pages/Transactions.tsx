// src/pages/Transactions.tsx (Screen 6)
import React from 'react'
import { useTransactions } from '../api/hooks'
import { TransactionTable } from '../components/payment/TransactionTable'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'
import { ErrorState } from '../components/ui/ErrorState'
import { useNavigate } from 'react-router-dom'
import { ROUTES } from '../lib/constants'

export const Transactions: React.FC = () => {
  const { data: transactions = [], isLoading, error, refetch } = useTransactions()
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Settlement Audit Log</h1>
        <p className="text-sm text-slate-500 mt-1">
          Immutable ledger of all autonomous procurement transactions settled via PayPal Orders v2 Sandbox.
        </p>
      </div>

      {isLoading ? (
        <div className="py-24 text-center space-y-4">
          <Spinner size="lg" />
          <p className="text-sm text-slate-500 font-medium">Loading ledger transactions…</p>
        </div>
      ) : error ? (
        <ErrorState
          title="Could not load transactions"
          message={error.message}
          onRetry={() => refetch()}
        />
      ) : transactions.length === 0 ? (
        <EmptyState
          icon="💳"
          title="No transactions recorded"
          description="Autonomous agent transactions will appear here once plans are approved and settled."
          actionLabel="Deploy First Agent"
          onAction={() => navigate(ROUTES.home)}
        />
      ) : (
        <TransactionTable transactions={transactions} />
      )}
    </div>
  )
}
