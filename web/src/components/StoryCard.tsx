import { stripMarkdown } from '../lib/markdown'
import type { Story } from '../types'

const tierColors: Record<string, string> = {
  weekly: '#60A5FA',
  monthly: '#A78BFA',
  quarterly: '#F472B6',
  yearly: '#FB923C',
  'all-time': '#34D399',
}

const tierLabels: Record<string, string> = {
  weekly: 'Weekly',
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  yearly: 'Yearly',
  'all-time': 'All Time',
}

interface StoryCardProps {
  story: Story
  onClick: () => void
}

export function StoryCard({ story, onClick }: StoryCardProps) {
  const color = tierColors[story.tier] || 'var(--brand)'
  const plain = stripMarkdown(story.content)
  const preview = plain.length > 200 ? plain.slice(0, 200) + '...' : plain

  const period = story.period_start && story.period_end
    ? `${story.period_start} — ${story.period_end}`
    : story.period_start || ''

  return (
    <div className="story-card" onClick={onClick}>
      <div className="story-card__accent" style={{ background: color }} />
      <div className="story-card__header">
        <span className="story-card__tier" style={{ background: `${color}14`, color }}>
          {tierLabels[story.tier]}
        </span>
        {period && <span className="story-card__period">{period}</span>}
      </div>
      <div className="story-card__title">{story.title}</div>
      <div className="story-card__preview">{preview}</div>
      {story.tags && story.tags.length > 0 && (
        <div className="story-card__tags">
          {story.tags.slice(0, 4).map((tag) => (
            <span key={tag} className="tag">{tag}</span>
          ))}
        </div>
      )}
    </div>
  )
}
