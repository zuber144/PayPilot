// src/components/Nav.tsx
import { Link } from 'react-router-dom'

export function Nav() {
  return (
    <nav className="nav">
      <Link to="/" className="nav-brand">🚀 PayPilot AgentOS</Link>
      <Link to="/transactions">Transactions</Link>
    </nav>
  )
}
