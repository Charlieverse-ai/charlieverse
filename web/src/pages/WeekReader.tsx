import { Markdown } from '../components/Markdown'
import { useStoriesInPeriod } from '../hooks/use-stories'
import { parseLocalDate, weekRangeLabel } from '../lib/dates'
import type { Story } from '../types'

interface WeekReaderProps {
  periodStart: string
  periodEnd: string
  /** Optional title override — otherwise falls back to "Week of <range>". */
  title?: string
  onBack: () => void
}

function dayHeader(story: Story): string {
  const dateStr = story.period_start || story.created_at
  const d = parseLocalDate(dateStr)
  return d.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })
}

function orderDailies(stories: Story[]): Story[] {
  // Chronological — oldest first — so a week reads forward in time.
  return [...stories].sort((a, b) => {
    const as = a.period_start || a.created_at
    const bs = b.period_start || b.created_at
    return as.localeCompare(bs)
  })
}

export function WeekReader({ periodStart, periodEnd, title, onBack }: WeekReaderProps) {
  const { data: dailies, isLoading } = useStoriesInPeriod('daily', periodStart, periodEnd)

  const heading = title || `Week of ${weekRangeLabel(periodStart, periodEnd)}`
  const ordered = orderDailies(dailies || [])

  return (
    <div className="reader">
      <button className="reader-back" onClick={onBack}>
        ← Back
      </button>
      <article className="reader-article prose">
        <header style={{ marginBottom: 32 }}>
          <h1 style={{ margin: 0 }}>{heading}</h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 13, marginTop: 6 }}>
            {weekRangeLabel(periodStart, periodEnd)}
            {ordered.length > 0 && ` · ${ordered.length} ${ordered.length === 1 ? 'day' : 'days'}`}
          </p>
        </header>

        {isLoading && (
          <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: '48px 0', fontSize: 13 }}>
            Loading dailies...
          </div>
        )}

        {!isLoading && ordered.length === 0 && (
          <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: '48px 0', fontSize: 13 }}>
            No daily stories for this week yet.
          </div>
        )}

        {ordered.map((story, i) => (
          <section
            key={story.id}
            style={{
              marginBottom: 48,
              paddingTop: i === 0 ? 0 : 32,
              borderTop: i === 0 ? 'none' : '1px solid var(--border)',
            }}
          >
            <div
              style={{
                fontSize: 12,
                fontWeight: 500,
                color: 'var(--text-tertiary)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                marginBottom: 6,
              }}
            >
              {dayHeader(story)}
            </div>
            <h2 style={{ marginTop: 0, marginBottom: 16 }}>{story.title}</h2>
            <Markdown content={story.content} />
          </section>
        ))}
      </article>
    </div>
  )
}
