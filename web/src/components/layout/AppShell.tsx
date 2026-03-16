import { useState, useEffect, useCallback, useRef } from 'react'
import { Menu } from 'lucide-react'
import { Sidebar, type Page } from './Sidebar'
import { Topbar } from './Topbar'
import { QuickFind } from '../QuickFind'
import { DetailModal } from '../DetailModal'
import { Dashboard } from '../../pages/Dashboard'
import { Memories } from '../../pages/Memories'
import { Sessions } from '../../pages/Sessions'
import { KnowledgePage } from '../../pages/Knowledge'
import { SettingsPage } from '../../pages/Settings'
import { StoryReader } from '../../pages/StoryReader'
import type { Entity, Knowledge, Session, Story } from '../../types'

type DetailItem =
  | { kind: 'entity'; data: Entity }
  | { kind: 'knowledge'; data: Knowledge }
  | { kind: 'session'; data: Session }
  | { kind: 'story'; data: Story }

type DetailSource = 'search' | 'page'

export function AppShell() {
  const [page, setPage] = useState<Page>('dashboard')
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [detailItem, setDetailItem] = useState<DetailItem | null>(null)
  const [detailSource, setDetailSource] = useState<DetailSource>('page')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [activeStory, setActiveStory] = useState<Story | null>(null)
  const [noAnimate, setNoAnimate] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('cv-theme') as 'dark' | 'light') || 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('cv-theme', theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  }, [])

  const handleNavigate = useCallback((p: Page) => {
    setPage(p)
    setActiveStory(null)
    setNoAnimate(true)
    setMobileMenuOpen(false)
    contentRef.current?.scrollTo(0, 0)
  }, [])

  // Browser history for story reader (enables swipe-back on iOS)
  const openStory = useCallback((story: Story) => {
    setNoAnimate(false)
    setActiveStory(story)
    history.pushState({ story: true }, '')
    contentRef.current?.scrollTo(0, 0)
  }, [])

  const closeStory = useCallback(() => {
    setNoAnimate(true)
    setActiveStory(null)
    contentRef.current?.scrollTo(0, 0)
  }, [])

  useEffect(() => {
    const handler = (e: PopStateEvent) => {
      if (activeStory) {
        e.preventDefault()
        closeStory()
      }
    }
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [activeStory, closeStory])

  // Tap topbar to scroll to top (iOS status bar tap equivalent)
  const handleTopbarTap = useCallback(() => {
    contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  // Global ⌘K handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchQuery('')
        setSearchOpen((v) => !v)
      }
      if (e.key === 'Escape') {
        if (detailItem) {
          if (detailSource === 'search') {
            setDetailItem(null)
            setSearchOpen(true)
          } else {
            setDetailItem(null)
          }
        }
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [detailItem, detailSource])

  const openEntity = useCallback((entity: Entity) => {
    setDetailItem({ kind: 'entity', data: entity })
    setDetailSource('page')
  }, [])

  const openKnowledge = useCallback((article: Knowledge) => {
    setDetailItem({ kind: 'knowledge', data: article })
    setDetailSource('page')
  }, [])

  const openSession = useCallback((session: Session) => {
    setDetailItem({ kind: 'session', data: session })
    setDetailSource('page')
  }, [])

  const openEntityFromSearch = useCallback((entity: Entity) => {
    setDetailItem({ kind: 'entity', data: entity })
    setDetailSource('search')
    setSearchOpen(false)
  }, [])

  const openKnowledgeFromSearch = useCallback((article: Knowledge) => {
    setDetailItem({ kind: 'knowledge', data: article })
    setDetailSource('search')
    setSearchOpen(false)
  }, [])

  const searchTag = useCallback((tag: string) => {
    setDetailItem(null)
    setSearchQuery(tag)
    setSearchOpen(true)
  }, [])

  const handleDetailClose = useCallback(() => {
    if (detailSource === 'search') {
      setDetailItem(null)
      setSearchOpen(true)
    } else {
      setDetailItem(null)
    }
  }, [detailSource])

  const handleStoryBack = useCallback(() => {
    // Pop the history entry we pushed when opening
    history.back()
  }, [])

  return (
    <div className="app">
      {mobileMenuOpen && (
        <div className="mobile-overlay" onClick={() => setMobileMenuOpen(false)} />
      )}
      <Sidebar
        activePage={page}
        onNavigate={handleNavigate}
        onOpenSearch={() => { setSearchQuery(''); setSearchOpen(true); setMobileMenuOpen(false) }}
        theme={theme}
        onToggleTheme={toggleTheme}
        className={mobileMenuOpen ? 'mobile-open' : ''}
      />
      <div className="main">
        <Topbar
          page={page}
          activeStory={activeStory}
          onStoryBack={handleStoryBack}
          onTap={handleTopbarTap}
          mobileMenuButton={
            <button className="mobile-burger" onClick={() => setMobileMenuOpen(true)}>
              <Menu size={20} strokeWidth={1.75} />
            </button>
          }
        />
        <div className="content" ref={contentRef}>
          {activeStory ? (
            <StoryReader story={activeStory} onBack={handleStoryBack} />
          ) : (
            <div className={noAnimate ? 'no-animate' : ''}>
              {page === 'dashboard' && <Dashboard onSelectStory={openStory} />}
              {page === 'memories' && <Memories onSelect={openEntity} onTagClick={searchTag} />}
              {page === 'sessions' && <Sessions onSelect={openSession} />}
              {page === 'knowledge' && <KnowledgePage onSelect={openKnowledge} onTagClick={searchTag} />}
              {page === 'settings' && <SettingsPage />}
            </div>
          )}
        </div>
      </div>

      <QuickFind
        open={searchOpen}
        initialQuery={searchQuery}
        onClose={() => setSearchOpen(false)}
        onSelectEntity={openEntityFromSearch}
        onSelectKnowledge={openKnowledgeFromSearch}
      />

      <DetailModal
        item={detailItem}
        onClose={handleDetailClose}
        onDismiss={() => setDetailItem(null)}
        onTagClick={searchTag}
        showBack={detailSource === 'search'}
      />
    </div>
  )
}
