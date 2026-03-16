import { ArrowLeft } from 'lucide-react'
import type { Page } from './Sidebar'
import type { Story } from '../../types'

const pageTitles: Record<Page, string> = {
  dashboard: 'Activity',
  memories: 'Memories',
  sessions: 'Sessions',
  knowledge: 'Knowledge',
  settings: 'Settings',
}

const pageDescriptions: Record<Page, string> = {
  dashboard: '',
  memories: 'Decisions, solutions, preferences, and moments.',
  sessions: 'Your conversation history.',
  knowledge: 'Expertise and domain knowledge articles.',
  settings: 'Server configuration and maintenance.',
}

interface TopbarProps {
  page: Page
  activeStory?: Story | null
  onStoryBack?: () => void
  onTap?: () => void
  mobileMenuButton?: React.ReactNode
}

export function Topbar({ page, activeStory, onStoryBack, onTap, mobileMenuButton }: TopbarProps) {
  if (activeStory) {
    return (
      <div className="topbar" onClick={onTap}>
        <div className="topbar-left">
          {mobileMenuButton}
          <button className="topbar-back" onClick={(e) => { e.stopPropagation(); onStoryBack?.() }}>
            <ArrowLeft size={16} strokeWidth={2} />
          </button>
          <div>
            <div className="topbar-title">{activeStory.title}</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="topbar" onClick={onTap}>
      <div className="topbar-left">
        {mobileMenuButton}
        <div>
          <div className="topbar-title">{pageTitles[page]}</div>
          {pageDescriptions[page] && (
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 1 }}>
              {pageDescriptions[page]}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
