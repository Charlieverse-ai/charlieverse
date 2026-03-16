import { useState } from 'react'
import { useEntities } from '../hooks/use-entities'
import { EntityCard } from '../components/EntityCard'
import { FilterChips } from '../components/FilterChips'
import type { Entity, EntityType } from '../types'

interface MemoriesProps {
  onSelect: (entity: Entity) => void
  onTagClick: (tag: string) => void
}

export function Memories({ onSelect, onTagClick }: MemoriesProps) {
  const [typeFilter, setTypeFilter] = useState<EntityType | null>(null)
  const { data: entities, isLoading } = useEntities(typeFilter || undefined)

  const pinned = entities?.filter((e) => e.pinned) || []
  const rest = entities?.filter((e) => !e.pinned) || []

  return (
    <div>
      <FilterChips active={typeFilter} onChange={setTypeFilter} />

      {isLoading && (
        <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: '48px 0', fontSize: 14 }}>
          Loading...
        </div>
      )}

      {!isLoading && entities?.length === 0 && (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
          <div>No memories found</div>
        </div>
      )}

      {/* Pinned / featured */}
      {pinned.length > 0 && (
        <>
          <div className="section-head" style={{ marginTop: 0 }}>
            <div className="section-title">Pinned</div>
          </div>
          <div className="entity-grid entity-grid--featured">
            {pinned.map((entity) => (
              <EntityCard
                key={entity.id}
                entity={entity}
                featured
                onClick={() => onSelect(entity)}
                onTagClick={onTagClick}
              />
            ))}
          </div>
        </>
      )}

      {/* Rest */}
      {rest.length > 0 && (
        <>
          {pinned.length > 0 && (
            <div className="section-head">
              <div className="section-title">All memories</div>
            </div>
          )}
          <div className="entity-grid">
            {rest.map((entity) => (
              <EntityCard
                key={entity.id}
                entity={entity}
                onClick={() => onSelect(entity)}
                onTagClick={onTagClick}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
