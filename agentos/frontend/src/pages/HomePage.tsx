// src/pages/HomePage.tsx — goal creation form with 3 one-click demo goals
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api'
import { formatMoney } from '../components/Money'

const DEMO_GOALS = [
  {
    label: '🌐 Website + Copywriting',
    raw_text: 'Build a professional website and write compelling copy for my SaaS product. I need it in 3 weeks and want great quality.',
    budget_minor: 200000,
    currency: 'USD',
  },
  {
    label: '🎨 Logo Design',
    raw_text: 'Design a logo for my new brand. Keep it simple and affordable.',
    budget_minor: 20000,
    currency: 'USD',
  },
  {
    label: '✍️ Content Writing',
    raw_text: 'Write content and blog posts for my marketing campaign. Need stuff written fast and cheap.',
    budget_minor: 25000,
    currency: 'USD',
  },
]

export function HomePage() {
  const navigate = useNavigate()
  const [rawText, setRawText] = useState('')
  const [budgetDollars, setBudgetDollars] = useState('')
  const [currency] = useState('USD')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: api.createGoal,
    onSuccess: (goal) => navigate(`/goals/${goal.id}`),
    onError: (e: Error) => setError(e.message),
  })

  const submit = (text: string, budget: number, cur: string) => {
    setError(null)
    mutation.mutate({ raw_text: text, budget_minor: budget, currency: cur, user_id: 1 })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const budget = Math.round(parseFloat(budgetDollars) * 100)
    if (!rawText.trim() || isNaN(budget) || budget <= 0) {
      setError('Please enter a goal description and a valid budget.')
      return
    }
    submit(rawText, budget, currency)
  }

  return (
    <div className="container">
      <h1>🚀 PayPilot AgentOS</h1>
      <p className="text-muted mb-2">Describe your project goal and let AI find the best providers, negotiate prices, and generate a plan — with built-in PayGuard compliance.</p>

      <div className="card">
        <h2>New Goal</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="raw_text">What do you need done?</label>
            <textarea
              id="raw_text"
              rows={4}
              placeholder="e.g. Build a landing page and write copy for my new product launch..."
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="budget">Budget (USD)</label>
            <input
              id="budget"
              type="number"
              min="1"
              step="0.01"
              placeholder="e.g. 1000"
              value={budgetDollars}
              onChange={(e) => setBudgetDollars(e.target.value)}
            />
          </div>
          {error && <div className="error-box">{error}</div>}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Starting…' : 'Start Agent Pipeline →'}
          </button>
        </form>
      </div>

      <div className="card">
        <h2>⚡ One-Click Demo Goals</h2>
        <p className="text-muted text-sm mb-2">Each demo goal produces a different PayGuard outcome.</p>
        <div className="flex gap-1" style={{ flexDirection: 'column' }}>
          {DEMO_GOALS.map((demo, i) => (
            <button
              key={i}
              className="btn btn-secondary"
              style={{ textAlign: 'left', padding: '0.75rem 1rem' }}
              onClick={() => submit(demo.raw_text, demo.budget_minor, demo.currency)}
              disabled={mutation.isPending}
            >
              <strong>{demo.label}</strong>
              <span className="text-muted text-sm" style={{ display: 'block' }}>
                Budget: {formatMoney(demo.budget_minor, demo.currency)} —{' '}
                {i === 0 ? 'Expected: APPROVED' : i === 1 ? 'Expected: REVIEW' : 'Expected: BLOCKED'}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
