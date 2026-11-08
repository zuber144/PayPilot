// src/components/StatusBadge.tsx
interface Props { status: string }

const statusClass: Record<string, string> = {
  NEW: 'badge-gray', RUNNING: 'badge-blue', PLANNED: 'badge-green', FAILED: 'badge-red',
  DRAFT: 'badge-gray', CHECKED: 'badge-blue', APPROVED: 'badge-green',
  PAYING: 'badge-blue', PAID: 'badge-green', BLOCKED: 'badge-red', PAY_FAILED: 'badge-red',
  CREATED: 'badge-blue', COMPLETED: 'badge-green',
  OPENING: 'badge-gray', COUNTERED: 'badge-yellow', FINAL: 'badge-blue', SELECTED: 'badge-green',
}

export function StatusBadge({ status }: Props) {
  return (
    <span className={`badge ${statusClass[status] ?? 'badge-gray'}`}>
      {status}
    </span>
  )
}
