// src/components/layout/NavBar.tsx
import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ROUTES } from '../../lib/constants'

export const NavBar: React.FC = () => {
  const location = useLocation()

  const isActive = (path: string) => {
    if (path === '/' && location.pathname === '/') return true
    if (path !== '/' && location.pathname.startsWith(path)) return true
    return false
  }

  return (
    <header className="bg-navy-600 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <Link to={ROUTES.home} className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg bg-paypal-500 flex items-center justify-center font-black text-lg text-white shadow-inner group-hover:scale-105 transition-transform">
              P
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight">PayPilot</span>{' '}
              <span className="text-xs bg-navy-800 text-paypal-100 px-2 py-0.5 rounded font-mono uppercase tracking-wider ml-1">
                AgentOS
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1 sm:gap-2">
            <Link
              to={ROUTES.home}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive(ROUTES.home)
                  ? 'bg-navy-700 text-white'
                  : 'text-slate-200 hover:bg-navy-700 hover:text-white'
              }`}
            >
              Goal Dashboard
            </Link>
            <Link
              to={ROUTES.transactions}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive(ROUTES.transactions)
                  ? 'bg-navy-700 text-white'
                  : 'text-slate-200 hover:bg-navy-700 hover:text-white'
              }`}
            >
              Transactions
            </Link>
          </nav>
        </div>
      </div>
    </header>
  )
}
