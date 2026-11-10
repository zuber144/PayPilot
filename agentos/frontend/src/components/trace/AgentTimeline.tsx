// src/components/trace/AgentTimeline.tsx
import React from 'react'
import type { TraceEvent } from '../../api/types'
import { TraceEventRow } from './TraceEventRow'

interface AgentTimelineProps {
  trace: TraceEvent[]
  isRunning?: boolean
}

export const AgentTimeline: React.FC<AgentTimelineProps> = ({ trace, isRunning = false }) => {
  if (!trace || trace.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-slate-400">
        No trace events recorded yet. Waiting for pipeline execution…
      </div>
    )
  }

  return (
    <div className="space-y-0.5">
      {trace.map((event, idx) => {
        const isLast = idx === trace.length - 1
        const isActive = isRunning && isLast
        return (
          <TraceEventRow
            key={`${event.step}-${idx}`}
            event={event}
            isLast={isLast && !isRunning}
            isActive={isActive}
          />
        )
      })}
      {isRunning && (
        <div className="relative flex items-center gap-3 pt-1 animate-pulse">
          <div className="w-7 h-7 rounded-full bg-blue-50 border border-blue-300 flex items-center justify-center">
            <span className="w-2 h-2 rounded-full bg-paypal-500 animate-ping" />
          </div>
          <span className="text-xs text-slate-500 font-medium italic">
            Executing next agent step…
          </span>
        </div>
      )}
    </div>
  )
}
