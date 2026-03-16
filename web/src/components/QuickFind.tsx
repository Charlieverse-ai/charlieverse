import { useState, useEffect, useRef, useCallback } from 'react'
import { Search } from 'lucide-react'
import { cn } from '../lib/utils'
import { entityColors } from '../lib/colors'
import { useSearch } from '../hooks/use-search'
import type { Entity, Knowledge } from '../types'

interface QuickFindProps {
  open: boolean
  initialQuery?: string
  onClose: () => void
  onSelectEntity: (entity: Entity) => void
  onSelectKnowledge: (article: Knowledge) => void
}

type ResultItem =
  | { kind: 'entity'; data: Entity }
  | { kind: 'knowledge'; data: Knowledge }

export function QuickFind({ open, initialQuery = '', onClose, onSelectEntity, onSelectKnowledge }: QuickFindProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const { data } = useSearch(query)

  // Build flat result list
  const results: ResultItem[] = []
  if (data) {
    for (const e of data.entities) results.push({ kind: 'entity', data: e })
    for (const k of data.knowledge) results.push({ kind: 'knowledge', data: k })
  }

  useEffect(() => {
    if (open) {
      setQuery(initialQuery)
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0)
  }, [data])

  const selectItem = useCallback((item: ResultItem) => {
    if (item.kind === 'entity') onSelectEntity(item.data)
    else onSelectKnowledge(item.data)
    onClose()
  }, [onSelectEntity, onSelectKnowledge, onClose])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
      return
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((i) => Math.min(i + 1, results.length - 1))
      return
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((i) => Math.max(i - 1, 0))
      return
    }

    if (e.key === 'Enter' && results.length > 0) {
      e.preventDefault()
      selectItem(results[selectedIndex])
      return
    }
  }

  // Scroll selected item into view
  useEffect(() => {
    if (!resultsRef.current) return
    const items = resultsRef.current.querySelectorAll('.qf-item')
    const selected = items[selectedIndex]
    if (selected) {
      selected.scrollIntoView({ block: 'nearest' })
    }
  }, [selectedIndex])

  return (
    <div
      className={cn('qf-overlay', open && 'open')}
      onClick={onClose}
    >
      <div className="qf-box" onClick={(e) => e.stopPropagation()}>
        <div className="qf-input-row">
          <span className="qf-icon"><Search size={20} /></span>
          <input
            ref={inputRef}
            className="qf-input"
            placeholder="Search memories, knowledge, sessions..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <div className="qf-results" ref={resultsRef}>
          {!query && (
            <div className="qf-hint">Type to search across all your data</div>
          )}
          {query && results.length === 0 && (
            <div className="qf-hint">No results for "{query}"</div>
          )}
          {query.length > 1 && results.map((item, i) => {
            const isEntity = item.kind === 'entity'
            const e = isEntity ? item.data as Entity : null
            const k = !isEntity ? item.data as Knowledge : null

            return (
              <div
                key={isEntity ? e!.id : k!.id}
                className={cn('qf-item', i === selectedIndex && 'selected')}
                onClick={() => selectItem(item)}
                onMouseEnter={() => setSelectedIndex(i)}
              >
                <span
                  className="qf-item-dot"
                  style={{
                    background: isEntity
                      ? entityColors[e!.type]
                      : 'var(--knowledge-color)',
                  }}
                />
                <span className="qf-item-text">
                  {isEntity
                    ? e!.content.split('\n')[0].slice(0, 80)
                    : k!.topic}
                </span>
                <span className="qf-item-kind">
                  {isEntity ? e!.type : 'knowledge'}
                </span>
              </div>
            )
          })}
        </div>
        <div className="qf-footer">
          <span><kbd>&uarr;</kbd> <kbd>&darr;</kbd> Navigate</span>
          <span><kbd>&crarr;</kbd> Open</span>
          <span><kbd>esc</kbd> Close</span>
        </div>
      </div>
    </div>
  )
}
