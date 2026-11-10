// src/components/layout/AppShell.tsx
import React from 'react'
import { Outlet } from 'react-router-dom'
import { DemoBanner } from './DemoBanner'
import { NavBar } from './NavBar'

export const AppShell: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <DemoBanner />
      <NavBar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        PayPal AgentOS + PayGuard AI &bull; Autonomous Procurement with Deterministic Guardrails
      </footer>
    </div>
  )
}
