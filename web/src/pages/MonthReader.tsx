import { Markdown } from '../components/Markdown'
import { useStoriesInPeriod } from '../hooks/use-stories'
import { parseLocalDate, weekRangeLabel } from '../lib/dates'
import type { Story } from '../types'

interface MonthReaderProps {
  periodStart: string
  periodEnd: string
  /** Optional title override — otherwise "Month of <month year>". */
  title?: string
  /** Monthly rollup to render when no weekly stories exist for this period. */
  fallbackStory?: Story
  onBack: () => void
  onSelectWeek: (week: { periodStart: string; periodEnd: string; title?: string }) => void
}

function monthLabel(start: string): string {
  return parseLocalDate(start).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}

function orderWeeks(stories: Story[]): Story[] {
  // Newest week at the top.
  return [...stories].sort((a, b) => (b.period_start || '').localeCompare(a.period_start || ''))
}

function firstSentence(content: string): string {
  const lines = content.split('\n')
  const chunks: string[] = []
  let foundContent = false
  for (const line of lines) {
    const trimmed = line.trim()
    if (!foundContent) {
      if (!trimmed || trimmed.startsWith('#') || trimmed === '---' || /^\*\*[A-Z]/.test(trimmed)) continue
      foundContent = true
    }
    if (foundContent) {
      if (!trimmed && chunks.length > 0) break
      if (trimmed.startsWith('#') || trimmed === '---') break
      chunks.push(trimmed)
    }
  }
  const joined = chunks.join(' ')
  return joined.length > 300 ? joined.slice(0, 300) + '...' : joined
}

export function MonthReader({ periodStart, periodEnd, title, fallbackStory, onBack, onSelectWeek }: MonthReaderProps) {
  const { data: weeklies, isLoading } = useStoriesInPeriod('weekly', periodStart, periodEnd)

  const heading = title || monthLabel(periodStart)
  const ordered = orderWeeks(weeklies || [])
  const hasWeeks = ordered.length > 0
  const showFallback = !isLoading && !hasWeeks && !!fallbackStory

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
            {hasWeeks && ` · ${ordered.length} ${ordered.length === 1 ? 'week' : 'weeks'}`}
            {showFallback && ' · monthly summary'}
          </p>
        </header>

        {isLoading && (
          <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: '48px 0', fontSize: 13 }}>
            Loading weeks...
          </div>
        )}

        {showFallback && <Markdown content={fallbackStory.content} />}

        {!isLoading && !hasWeeks && !fallbackStory && (
          <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: '48px 0', fontSize: 13 }}>
            No weekly stories for this month yet.
          </div>
        )}

        <div className="chapter-weeks" style={{ marginTop: 0 }}>
          {ordered.map((story, i) => {
            const preview = firstSentence(story.content)
            const range = story.period_start && story.period_end
              ? weekRangeLabel(story.period_start, story.period_end)
              : story.title
            const clickable = !!(story.period_start && story.period_end)
            return (
              <div
                className="week-entry"
                key={story.id}
                onClick={() =>
                  clickable &&
                  onSelectWeek({
                    periodStart: story.period_start!,
                    periodEnd: story.period_end!,
                    title: story.title,
                  })
                }
                style={{ cursor: clickable ? 'pointer' : 'default' }}
              >
                <div className="week-entry__marker-col">
                  <div
                    className={`week-entry__dot ${i === 0 ? 'week-entry__dot--current' : ''}`}
                    style={{ background: '#60A5FA' }}
                  />
                  {i < ordered.length - 1 && <div className="week-entry__line" />}
                </div>
                <div className="week-entry__content">
                  <div className="week-entry__date">{range}</div>
                  <div className="week-entry__title">{story.title}</div>
                  <p className="week-entry__preview">{preview}</p>
                  <span className="week-entry__read">Open week →</span>
                </div>
              </div>
            )
          })}
        </div>
      </article>
    </div>
  )
}
