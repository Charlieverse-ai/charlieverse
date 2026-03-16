import { entityColors, entityLabels } from '../lib/colors'
import type { EntityType } from '../types'

export function TypeBadge({ type }: { type: EntityType }) {
  const color = entityColors[type]
  return (
    <span
      className="text-xs font-medium font-mono px-1.5 py-0.5 rounded uppercase tracking-wide"
      style={{ background: `${color}18`, color }}
    >
      {entityLabels[type]}
    </span>
  )
}
