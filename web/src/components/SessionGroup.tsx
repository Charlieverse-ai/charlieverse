import { relativeTime } from '../lib/dates'
import type { Session } from '../types'
import { Markdown } from './Markdown'
interface SessionGroupProps {
  sessions: Session[]
  onSelect: (session: Session) => void
}



function sessionSummary(what: string): string | null {
  const lines = what.split('\n')
  // Find first markdown header (### Something) as a summary of key topics
  const headers: string[] = []
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('### ')) {
      headers.push(trimmed.replace(/^###\s*/, ''))
    }
  }
  if (headers.length > 0) {
    return headers.slice(0, 5).join(' · ')
  }
  return null
}

export function SessionGroup({ sessions, onSelect }: SessionGroupProps) {
  return (
    <div>
      {sessions.map((session) => {
        const summary = sessionSummary(session.what_happened || '')
        return (
          <div
            key={session.id}
            className="session-row"
            onClick={() => onSelect(session)}
          >
            <div className="session-row__bar" />
            <div className="session-row__body">
              <div className="session-row__title">
                <Markdown content={session.what_happened || ''} />
                </div>
              {summary && (
                <div className="session-row__summary">{summary}</div>
              )}
            </div>
            <div className="session-row__time">{relativeTime(session.created_at)}</div>
          </div>
        )
      })}
    </div>
  )
}
