import { useState } from 'react'
import { useStories } from '../hooks/use-stories'
import { StoryCard } from '../components/StoryCard'
import type { Story, StoryTier } from '../types'

const tiers: { value: StoryTier | null; label: string }[] = [
  { value: null, label: 'All' },
  { value: 'all-time', label: 'All Time' },
  { value: 'yearly', label: 'Yearly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'daily', label: 'Daily' },
  { value: 'session', label: 'Session' },
]

interface StoriesProps {
  onSelect: (story: Story) => void
}

export function StoriesPage({ onSelect }: StoriesProps) {
  const [activeTier, setActiveTier] = useState<StoryTier | null>(null)
  const { data: stories, isLoading } = useStories(activeTier || undefined)

  return (
    <div>
      <div className="flex gap-2.5 flex-wrap mb-8">
        {tiers.map(({ value, label }) => (
          <button
            key={label}
            className={`chip ${activeTier === value ? 'active' : ''}`}
            onClick={() => setActiveTier(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: '48px 0', fontSize: 13 }}>
          Loading...
        </div>
      )}

      {!isLoading && stories?.length === 0 && (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
          </svg>
          <div>No stories yet</div>
        </div>
      )}

      <div className="story-grid">
        {stories?.map((story) => (
          <StoryCard
            key={story.id}
            story={story}
            onClick={() => onSelect(story)}
          />
        ))}
      </div>
    </div>
  )
}
