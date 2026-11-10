// src/components/trace/TraceEventRow.tsx
import React, { useState } from 'react'
import type { TraceEvent } from '../../api/types'
import { formatDuration } from '../../lib/time'
import { RetryChip } from './RetryChip'

interface TraceEventRowProps {
  event: TraceEvent
  isLast?: boolean
  isActive?: boolean
}

export const TraceEventRow: React.FC<TraceEventRowProps> = ({ event, isLast = false, isActive = false }) => {
  const [expanded, setExpanded] = useState(false)

  const statusIcons = {
    OK: '✓',
    RETRY: '↺',
    FALLBACK: '⚡',
    ERROR: '✕',
  }

  const statusColors = {
    OK: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    RETRY: 'bg-amber-100 text-amber-800 border-amber-300',
    FALLBACK: 'bg-slate-100 text-slate-700 border-slate-300',
    ERROR: 'bg-red-100 text-red-800 border-red-300',
  }

  return (
    <div className="relative flex items-start gap-3 group animate-fade-in">
      {/* Vertical connection line */}
      {!isLast && (
        <span
          className="absolute left-3.5 top-7 -bottom-3 w-0.5 bg-slate-200"
          aria-hidden="true"
        />
      )}

      {/* Node status dot / icon */}
      <div
        className={`relative z-10 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border transition-all ${
          statusColors[event.status] || statusColors.OK
        } ${isActive ? 'ring-4 ring-paypal-100 ring-offset-1 animate-pulse' : ''}`}
      >
        {statusIcons[event.status] || '•'}
      </div>

      {/* Content card */}
      <div className="flex-1 pb-4">
        <div
          onClick={() => setExpanded(!expanded)}
          className="p-3 bg-white border border-slate-200 rounded-lg shadow-xs hover:border-slate-300 transition-colors cursor-pointer select-none"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs uppercase tracking-wider text-navy-600 font-mono">
                {event.step}
              </span>
              {event.status === 'RETRY' && <RetryChip count={event.retry_count} />}
              {event.used_fallback && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                  FALLBACK
                </span>
              )}
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              {formatDuration(event.duration_ms)}
            </span>
          </div>

          <p className="text-xs text-slate-700 leading-relaxed">{event.summary}</p>

          {/* Audit hash or expandable toggle */}
          {(event.hash || event.detail) && (
            <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
              {event.hash ? (
                <span className="font-mono truncate max-w-[200px]" title={event.hash}>
                  hash: {event.hash.substring(0, 12)}…
                </span>
              ) : (
                <span />
              )}
              <span className="text-paypal-600 font-medium">
                {expanded ? 'Hide payload ▲' : 'Inspect payload ▼'}
              </span>
            </div>
          )}
        </div>

        {/* Expanded detail payload */}
        {expanded && (
          <div className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-lg text-[11px] font-mono overflow-x-auto shadow-inner">
            <pre className="whitespace-pre-wrap">{JSON.stringify(event, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  )
}
