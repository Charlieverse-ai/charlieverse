import { useStories } from '../hooks/use-stories'
import type { Story } from '../types'

const tierColors: Record<string, string> = {
  weekly: '#60A5FA',
  monthly: '#A78BFA',
  quarterly: '#F472B6',
  yearly: '#FB923C',
  'all-time': '#34D399',
}

interface DashboardProps {
  onSelectStory: (story: Story) => void
}

function firstSentence(content: string): string {
  const lines = content.split('\n')
  const chunks: string[] = []

  let foundContent = false
  for (const line of lines) {
    const trimmed = line.trim()
    if (!foundContent) {
      if (!trimmed || trimmed.startsWith('#') || trimmed === '---' || trimmed.startsWith('**March') || trimmed.startsWith('**Week') || trimmed.startsWith('**Feb') || trimmed.startsWith('**Jan') || trimmed.startsWith('**Nov') || trimmed.startsWith('**Dec')) continue
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

function storySubtitle(content: string): string | null {
  const lines = content.split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('# ') && trimmed.includes('—')) {
      const parts = trimmed.split('—')
      if (parts.length > 1) return parts.slice(1).join('—').trim()
    }
  }
  return null
}

function contentTitle(content: string): string | null {
  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (trimmed.startsWith('# ') && !trimmed.startsWith('## ')) {
      return trimmed.replace(/^#\s+/, '')
    }
  }
  return null
}

function contentDateRange(content: string): string | null {
  for (const line of content.split('\n')) {
    const trimmed = line.trim()
    if (trimmed.startsWith('## ') && /\d{4}/.test(trimmed)) {
      return trimmed.replace(/^##\s+/, '')
    }
  }
  return null
}

function chapterSubtitle(content: string): string | null {
  const title = contentTitle(content)
  if (!title) return null
  // H1s look like "March 2026: The Month Everything Became Real"
  // or "February 2026 — The Month Charlieverse Was Born"
  const colonSplit = title.split(':')
  if (colonSplit.length > 1) return colonSplit.slice(1).join(':').trim()
  const dashSplit = title.split('—')
  if (dashSplit.length > 1) return dashSplit.slice(1).join('—').trim()
  return null
}


function monthKey(dateStr: string | null): string {
  if (!dateStr) return 'unknown'
  // Parse date parts directly to avoid UTC→local timezone shift
  // (e.g. "2026-03-01" parsed as UTC = Feb 28 in EST)
  const parts = dateStr.split('T')[0].split('-')
  return `${parts[0]}-${parts[1]}`
}

function monthLabel(key: string): string {
  if (key === 'unknown') return 'Unknown'
  const [year, month] = key.split('-')
  const d = new Date(parseInt(year), parseInt(month) - 1)
  return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}

function parseLocalDate(dateStr: string): Date {
  // Avoid UTC interpretation by constructing from parts
  const [y, m, d] = dateStr.split('T')[0].split('-').map(Number)
  return new Date(y, m - 1, d)
}

function weekLabel(story: Story): string {
  if (!story.period_start) return story.title
  const start = parseLocalDate(story.period_start)
  const end = story.period_end ? parseLocalDate(story.period_end) : null
  const startStr = start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  if (end) {
    const endStr = end.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return `${startStr} – ${endStr}`
  }
  return startStr
}

interface MonthGroup {
  key: string
  label: string
  monthly: Story | null
  weeks: Story[]
}

function groupByMonth(weekly: Story[], monthly: Story[]): MonthGroup[] {
  const groups = new Map<string, MonthGroup>()

  // Create groups from weekly stories
  for (const story of weekly) {
    const mk = monthKey(story.period_start)
    if (!groups.has(mk)) {
      groups.set(mk, { key: mk, label: monthLabel(mk), monthly: null, weeks: [] })
    }
    groups.get(mk)!.weeks.push(story)
  }

  // Attach monthly stories to their groups
  for (const story of monthly) {
    const mk = monthKey(story.period_start)
    if (groups.has(mk)) {
      groups.get(mk)!.monthly = story
    } else {
      groups.set(mk, { key: mk, label: monthLabel(mk), monthly: story, weeks: [] })
    }
  }

  // Sort groups by date descending
  return Array.from(groups.values()).sort((a, b) => b.key.localeCompare(a.key))
}

export function Dashboard({ onSelectStory }: DashboardProps) {
  const { data: weekly, isLoading: loadingWeekly } = useStories('weekly')
  const { data: monthly, isLoading: loadingMonthly } = useStories('monthly')
  const { data: allTime } = useStories('all-time')
  const { data: yearly } = useStories('yearly')
  const { data: quarterly } = useStories('quarterly')

  const isLoading = loadingWeekly || loadingMonthly

  // Pick the highest-tier story for the arc header
  const arcStory = allTime?.[0] || yearly?.[0] || quarterly?.[0] || null

  const groups = groupByMonth(weekly || [], monthly || [])

  if (isLoading) {
    return (
      <div className="dashboard-loading">
        <div className="arc-header-skeleton" />
        <div className="chapter-skeleton" />
        <div className="chapter-skeleton" />
      </div>
    )
  }

  if (!weekly?.length && !monthly?.length && !arcStory) {
    return (
      <div className="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
        <div>No stories yet</div>
      </div>
    )
  }

  // Groups are sorted newest first — reverse for chapter numbering (oldest = Chapter 1)
  const totalChapters = groups.length

  return (
    <div className="dashboard">
      {/* Chapters with nested weekly entries */}
      <div className="story-timeline">
        {groups.map((group, groupIdx) => {
          const chapterNum = totalChapters - groupIdx

          return (
          <div className="chapter" key={group.key}>
            {/* Chapter marker */}
            <div
              className={`chapter-header ${group.monthly ? 'chapter-header--has-story' : ''}`}
              onClick={group.monthly ? () => onSelectStory(group.monthly!) : undefined}
              style={group.monthly ? { cursor: 'pointer' } : undefined}
            >
              <div
                className="chapter-header__accent"
                style={{ background: tierColors.monthly }}
              />
              <div className="chapter-header__content">
                <div className="chapter-header__label">Chapter {chapterNum}</div>
                {group.monthly && chapterSubtitle(group.monthly.content) && (
                  <div className="chapter-header__title">{chapterSubtitle(group.monthly.content)}</div>
                )}
                {!chapterSubtitle(group.monthly?.content || '') && (
                  <div className="chapter-header__title">{group.label}</div>
                )}
                {group.monthly && (
                  <span className="chapter-header__read">Read chapter →</span>
                )}
              </div>
            </div>

            {/* Weekly entries nested under this month */}
            {group.weeks.length > 0 && (
              <div className="chapter-weeks">
                {group.weeks.map((story, i) => {
                  const isLatest = groups[0] === group && i === 0
                  const preview = firstSentence(story.content)
                  const subtitle = storySubtitle(story.content)

                  return (
                    <div
                      className="week-entry"
                      key={story.id}
                      onClick={() => onSelectStory(story)}
                    >
                      <div className="week-entry__marker-col">
                        <div
                          className={`week-entry__dot ${isLatest ? 'week-entry__dot--current' : ''}`}
                          style={{ background: tierColors.weekly }}
                        />
                        {i < group.weeks.length - 1 && (
                          <div className="week-entry__line" />
                        )}
                      </div>
                      <div className="week-entry__content">
                        <div className="week-entry__date">{weekLabel(story)}</div>
                        <div className="week-entry__title">{story.title}</div>
                        {subtitle && (
                          <div className="week-entry__subtitle">{subtitle}</div>
                        )}
                        <p className="week-entry__preview">{preview}</p>
                        <span className="week-entry__read">Read more →</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
          )
        })}
      </div>

      {/* Our Story — the full arc, at the end */}
      {arcStory && (
        <div
          className="arc-footer"
          onClick={() => onSelectStory(arcStory)}
          style={{ '--arc-color': tierColors[arcStory.tier] } as React.CSSProperties}
        >
          {contentDateRange(arcStory.content) && (
            <p className="arc-footer__date-range">{contentDateRange(arcStory.content)}</p>
          )}
          <span className="arc-footer__cta">Read the full story →</span>
        </div>
      )}
    </div>
  )
}
