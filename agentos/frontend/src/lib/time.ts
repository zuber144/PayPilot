// src/lib/time.ts — relative time helpers

/** e.g. "2m 3s" */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}m ${rem}s`
}

/** e.g. "just now", "3 minutes ago" */
export function timeAgo(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime()
  const s = Math.round(diff / 1000)
  if (s < 10) return 'just now'
  if (s < 60) return `${s}s ago`
  const m = Math.round(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.round(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.round(h / 24)}d ago`
}

/** Elapsed timer tick string from a start ISO string */
export function elapsedSince(isoString: string): string {
  return formatDuration(Date.now() - new Date(isoString).getTime())
}
