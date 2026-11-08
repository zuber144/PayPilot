// src/pages/GoalPage.tsx — polls goal status every 1.5s while RUNNING
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { StatusBadge } from '../components/StatusBadge'
import { Money } from '../components/Money'
import type { TraceEvent } from '../api/types'

function TraceDot({ status }: { status: string }) {
  return <span className={`timeline-dot ${status}`} />
}

function TraceStep({ event }: { event: TraceEvent }) {
  return (
    <div className="timeline-item">
      <TraceDot status={event.status} />
      <div>
        <strong>{event.step}</strong>{' '}
        <span className="text-muted text-sm">({event.duration_ms}ms)</span>
        {event.used_fallback && (
          <span className="badge badge-yellow" style={{ marginLeft: '0.5rem' }}>fallback</span>
        )}
        <div className="text-sm mt-1">{event.summary}</div>
      </div>
    </div>
  )
}

export function GoalPage() {
  const { id } = useParams<{ id: string }>()
  const goalId = parseInt(id ?? '0', 10)

  const { data: goal, error, isLoading } = useQuery({
    queryKey: ['goal', goalId],
    queryFn: () => api.getGoal(goalId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'RUNNING' || status === 'NEW' ? 1500 : false
    },
    enabled: goalId > 0,
  })

  const { data: offers } = useQuery({
    queryKey: ['goal-offers', goalId],
    queryFn: () => api.getGoalOffers(goalId),
    enabled: !!(goal && goal.status === 'PLANNED'),
  })

  if (isLoading) return <div className="container"><div className="spinner" /></div>
  if (error) return <div className="container"><div className="error-box">{(error as Error).message}</div></div>
  if (!goal) return <div className="container">Goal not found.</div>

  return (
    <div className="container">
      <div className="flex items-center gap-2 mb-2">
        <h1>Goal #{goal.id}</h1>
        <StatusBadge status={goal.status} />
        {(goal.status === 'RUNNING' || goal.status === 'NEW') && <span className="spinner" />}
      </div>

      <div className="card">
        <h2>Goal Details</h2>
        <p><strong>Description:</strong> {goal.raw_text}</p>
        <p><strong>Budget:</strong> <Money minor={goal.budget_minor} currency={goal.currency} /></p>
        {goal.parsed && (
          <p><strong>Needs:</strong> {goal.parsed.needs.join(', ')} · <strong>Deadline:</strong> {goal.parsed.deadline_days} days</p>
        )}
      </div>

      {goal.trace.length > 0 && (
        <div className="card">
          <h2>🤖 Agent Timeline</h2>
          <div className="timeline">
            {goal.trace.map((event, i) => (
              <TraceStep key={i} event={event} />
            ))}
          </div>
        </div>
      )}

      {goal.status === 'FAILED' && (
        <div className="error-box">Pipeline failed. Check the trace above for details.</div>
      )}

      {offers && offers.length > 0 && (
        <div className="card">
          <h2>📋 Offers</h2>
          <table>
            <thead>
              <tr>
                <th>Need</th>
                <th>Provider</th>
                <th>Price</th>
                <th>Timeline</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {offers.map((o) => (
                <tr key={o.id}>
                  <td>{o.need_key}</td>
                  <td>#{o.provider_id}</td>
                  <td><Money minor={o.price_minor} currency={goal.currency} /></td>
                  <td>{o.timeline_days}d</td>
                  <td><StatusBadge status={o.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {goal.plan_id && goal.status === 'PLANNED' && (
        <div className="card">
          <h2>✅ Plan Ready</h2>
          <Link to={`/plans/${goal.plan_id}`} className="btn btn-primary">
            View Plan →
          </Link>
        </div>
      )}
    </div>
  )
}
