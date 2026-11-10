// src/pages/NotFound.tsx (Screen 7)
import React from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { ROUTES } from '../lib/constants'

export const NotFound: React.FC = () => {
  return (
    <div className="py-24 text-center max-w-md mx-auto space-y-4">
      <div className="text-6xl font-black text-navy-600 font-mono">404</div>
      <h1 className="text-xl font-bold text-slate-900">Page Not Found</h1>
      <p className="text-xs text-slate-500">
        The requested procurement route or resource does not exist in AgentOS.
      </p>
      <div className="pt-2">
        <Link to={ROUTES.home}>
          <Button variant="primary" size="md">
            Return to Command Center
          </Button>
        </Link>
      </div>
    </div>
  )
}
