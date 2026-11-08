// src/pages/TransactionsPage.tsx — list all transactions
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'
import { Money } from '../components/Money'

export function TransactionsPage() {
  const { data: transactions, isLoading, error } = useQuery({
    queryKey: ['transactions'],
    queryFn: api.listTransactions,
  })

  if (isLoading) return <div className="container"><div className="spinner" /></div>
  if (error) return <div className="container"><div className="error-box">{(error as Error).message}</div></div>

  return (
    <div className="container">
      <h1>💰 Transactions</h1>

      {(!transactions || transactions.length === 0) ? (
        <div className="card">
          <p className="text-muted">No transactions yet. <Link to="/">Create a goal</Link> to get started.</p>
        </div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Plan</th>
                <th>PayPal Order</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id}>
                  <td>#{t.id}</td>
                  <td>
                    <Link to={`/plans/${t.plan_id}`}>Plan #{t.plan_id}</Link>
                  </td>
                  <td className="font-mono" style={{ fontSize: '0.8rem' }}>
                    {t.paypal_order_id}
                  </td>
                  <td><Money minor={t.amount_minor} currency={t.currency} /></td>
                  <td><StatusBadge status={t.status} /></td>
                  <td className="text-sm text-muted">
                    {new Date(t.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
