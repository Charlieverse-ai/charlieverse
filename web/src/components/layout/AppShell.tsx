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
import { api } from '../../api/client'
import type { Entity, Knowledge, Session, Story } from '../../types'

type DetailItem =
  | { kind: 'entity'; data: Entity }
  | { kind: 'knowledge'; data: Knowledge }
  | { kind: 'session'; data: Session }
  | { kind: 'story'; data: Story }

type DetailSource = 'search' | 'page' | 'permalink'

/** Parse hash routes like #/memories/{id}, #/stories/{id}, etc. */
function parseHash(hash: string): { kind: string; id: string } | null {
  const match = hash.match(/^#\/(memories|stories|sessions|knowledge)\/(.+)$/)
  if (!match) return null
  return { kind: match[1], id: match[2] }
}

/** Build a hash route for a detail item */
function hashForItem(item: DetailItem): string {
  switch (item.kind) {
    case 'entity': return `#/memories/${item.data.id}`
    case 'story': return `#/stories/${item.data.id}`
    case 'session': return `#/sessions/${item.data.id}`
    case 'knowledge': return `#/knowledge/${item.data.id}`
  }
}

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

  // Permalink: load detail from hash on mount
  useEffect(() => {
    const route = parseHash(window.location.hash)
    if (!route) return

    const load = async () => {
      try {
        if (route.kind === 'memories') {
          const data = await api.getEntity(route.id)
          setDetailItem({ kind: 'entity', data })
          setDetailSource('permalink')
          setPage('memories')
        } else if (route.kind === 'stories') {
          const data = await api.getStory(route.id)
          setDetailItem({ kind: 'story', data })
          setDetailSource('permalink')
          setPage('dashboard')
        } else if (route.kind === 'sessions') {
          const data = await api.getSession(route.id)
          setDetailItem({ kind: 'session', data })
          setDetailSource('permalink')
          setPage('sessions')
        } else if (route.kind === 'knowledge') {
          const data = await api.getKnowledge(route.id)
          setDetailItem({ kind: 'knowledge', data })
          setDetailSource('permalink')
          setPage('knowledge')
        }
      } catch {
        // Item not found — just show the page
        window.location.hash = ''
      }
    }
    load()
  }, [])

  // Permalink: update hash when detail opens/closes
  useEffect(() => {
    if (detailItem) {
      const hash = hashForItem(detailItem)
      if (window.location.hash !== hash) {
        window.location.hash = hash
      }
    } else if (window.location.hash.match(/^#\/(memories|stories|sessions|knowledge)\//)) {
      history.replaceState(null, '', window.location.pathname)
    }
  }, [detailItem])

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
