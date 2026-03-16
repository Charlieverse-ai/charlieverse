import { relativeTime } from '../lib/dates'
import type { Session } from '../types'

interface SessionGroupProps {
  sessions: Session[]
  onSelect: (session: Session) => void
}


function sessionTitle(what: string): string {
  // Strip "Session N. Day Month Date, ~Time." prefix
  let cleaned = what.replace(/^Session \d+\.?\s*/i, '')
  // Strip "Day Month Date, ~Time PM/AM." or "continued."
  cleaned = cleaned.replace(/^continued\.\s*/i, '')
  cleaned = cleaned.replace(/^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s+\w+\s+\d+,?\s*~?\d+[:\d]*\s*(AM|PM|am|pm)?\.?\s*-?\s*\d*[:\d]*\s*(AM|PM|am|pm)?\.?\s*/i, '')
  // Strip leading "Built and iterated on" / "Ran the" etc to get punchier
  cleaned = cleaned.trim()
  if (!cleaned) return 'Session'
  // Get first sentence or line
  const firstLine = cleaned.split('\n')[0].trim()
  // Strip markdown headers
  const noHeader = firstLine.replace(/^#+\s*/, '')
  return noHeader || 'Session'
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
        const title = sessionTitle(session.what_happened || '')
        const summary = sessionSummary(session.what_happened || '')
        return (
          <div
            key={session.id}
            className="session-row"
            onClick={() => onSelect(session)}
          >
            <div className="session-row__bar" />
            <div className="session-row__body">
              <div className="session-row__title">{title}</div>
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
