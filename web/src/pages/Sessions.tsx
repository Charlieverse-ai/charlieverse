import { useSessions } from '../hooks/use-sessions'
import { SessionGroup } from '../components/SessionGroup'
import { groupByDate } from '../lib/dates'
import type { Session } from '../types'

interface SessionsProps {
  onSelect: (session: Session) => void
}

export function Sessions({ onSelect }: SessionsProps) {
  const { data: sessions, isLoading } = useSessions()

  const grouped = sessions ? groupByDate(sessions) : []

  return (
    <div>
      {isLoading && (
        <div className="text-sm text-[var(--text-tertiary)] py-8 text-center">Loading...</div>
      )}

      {!isLoading && sessions?.length === 0 && (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <div>No sessions yet</div>
        </div>
      )}

      {grouped.map(([date, items]) => (
        <div key={date}>
          <div className="date-group-header">{date}</div>
          <SessionGroup sessions={items} onSelect={onSelect} />
        </div>
      ))}
    </div>
  )
}
