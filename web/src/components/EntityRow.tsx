import { Pin } from 'lucide-react'
import { entityColors } from '../lib/colors'
import { relativeTime } from '../lib/dates'
import { stripMarkdown } from '../lib/markdown'
import { TypeBadge } from './TypeBadge'
import type { Entity } from '../types'

interface EntityRowProps {
  entity: Entity
  onClick: () => void
}

export function EntityRow({ entity, onClick }: EntityRowProps) {
  const color = entityColors[entity.type]
  const plain = stripMarkdown(entity.content)

  return (
    <div className="row" onClick={onClick}>
      <div className="row-bar" style={{ background: color }} />
      <div className="row-body">
        <div className="row-title">{plain}</div>
        <div className="row-meta">
          <TypeBadge type={entity.type} />
          {entity.pinned && (
            <span className="text-[var(--brand)] flex items-center">
              <Pin size={12} />
            </span>
          )}
          <span className="text-[var(--text-tertiary)]">&middot;</span>
          <span>{relativeTime(entity.created_at)}</span>
        </div>
        {entity.tags && entity.tags.length > 0 && (
          <div className="flex gap-1 flex-wrap mt-1.5">
            {entity.tags.slice(0, 4).map((tag) => (
              <span key={tag} className="tag">{tag}</span>
            ))}
          </div>
        )}
      </div>
      <div className="row-time">{relativeTime(entity.created_at)}</div>
    </div>
  )
}
