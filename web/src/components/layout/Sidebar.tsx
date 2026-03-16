import { Activity, Sparkles, Clock, BookOpen, Settings, Search, Sun, Moon, LogOut } from 'lucide-react'
import { cn } from '../../lib/utils'

export type Page = 'dashboard' | 'memories' | 'sessions' | 'knowledge' | 'settings'

interface SidebarProps {
  activePage: Page
  onNavigate: (page: Page) => void
  onOpenSearch: () => void
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  className?: string
}

export function Sidebar({ activePage, onNavigate, onOpenSearch, theme, onToggleTheme, className = '' }: SidebarProps) {
  return (
    <nav className={`sidebar ${className}`}>
      <div className="sidebar-search" onClick={onOpenSearch}>
        <Search size={16} strokeWidth={1.75} />
        <span className="sidebar-search-text">Search</span>
        <kbd>&#8984;K</kbd>
      </div>

      <div style={{ height: 10 }} />

      <div className="sidebar-section">
        <div
          className={cn('sidebar-item', activePage === 'dashboard' && 'active')}
          onClick={() => onNavigate('dashboard')}
        >
          <span className="sidebar-icon"><Activity size={18} strokeWidth={1.75} /></span>
          Activity
        </div>
        <div className="sidebar-section-label">Library</div>
        {([
          { page: 'memories' as const, label: 'Memories', icon: Sparkles },
          { page: 'sessions' as const, label: 'Sessions', icon: Clock },
          { page: 'knowledge' as const, label: 'Knowledge', icon: BookOpen },
        ]).map(({ page, label, icon: Icon }) => (
          <div
            key={page}
            className={cn('sidebar-item', activePage === page && 'active')}
            onClick={() => onNavigate(page)}
          >
            <span className="sidebar-icon"><Icon size={18} strokeWidth={1.75} /></span>
            {label}
          </div>
        ))}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-label">Configure</div>
        <div
          className={cn('sidebar-item', activePage === 'settings' && 'active')}
          onClick={() => onNavigate('settings')}
        >
          <span className="sidebar-icon"><Settings size={18} strokeWidth={1.75} /></span>
          Settings
        </div>
      </div>

      <div className="sidebar-bottom">
        <button className="sidebar-bottom-item" onClick={onToggleTheme}>
          {theme === 'dark' ? <Sun size={18} strokeWidth={1.75} /> : <Moon size={18} strokeWidth={1.75} />}
          <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
        </button>

        <div className="sidebar-profile">
          <div className="sidebar-avatar">C</div>
          <div className="sidebar-profile-info">
            <div className="sidebar-profile-name">Charlie</div>
            <div className="sidebar-profile-email">charlieverse.ai</div>
          </div>
          <LogOut size={16} strokeWidth={1.75} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
        </div>
      </div>
    </nav>
  )
}
