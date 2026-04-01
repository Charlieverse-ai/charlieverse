import { Pin } from 'lucide-react'
import { entityColors, entityLabels } from '../lib/colors'
import { relativeTime } from '../lib/dates'
import { stripMarkdown } from '../lib/markdown'
import type { Entity } from '../types'

interface EntityCardProps {
  entity: Entity
  featured?: boolean
  onClick: () => void
  onTagClick?: (tag: string) => void
}

export function EntityCard({ entity, featured = false, onClick, onTagClick: _onTagClick }: EntityCardProps) {
  const color = entityColors[entity.type]
  const plain = stripMarkdown(entity.content)

  return (
    <div
      className={featured ? 'entity-card entity-card--featured' : 'entity-card'}
      style={{ '--accent': color } as React.CSSProperties}
      onClick={onClick}
    >
      <div className="entity-card__header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {entity.pinned && (
            <span className="entity-card__pin">
              <Pin size={11} /> Pinned
            </span>
          )}
          <span className="entity-card__type" style={{ background: `${color}14`, color }}>
            {entityLabels[entity.type]}
          </span>
        </div>
        <span className="entity-card__time">{relativeTime(entity.created_at)}</span>
      </div>

      <div className="entity-card__content">{plain}</div>
    </div>
  )
}
