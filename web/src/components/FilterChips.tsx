import { entityColors, entityLabels } from '../lib/colors'
import { cn } from '../lib/utils'
import type { EntityType } from '../types'

const types: EntityType[] = ['decision', 'solution', 'preference', 'person', 'milestone', 'moment']

interface FilterChipsProps {
  active: EntityType | null
  onChange: (type: EntityType | null) => void
}

export function FilterChips({ active, onChange }: FilterChipsProps) {
  return (
    <div className="flex gap-2.5 flex-wrap mb-8">
      <button
        className={cn(
          'chip',
          active === null && 'active'
        )}
        onClick={() => onChange(null)}
      >
        All
      </button>
      {types.map((type) => (
        <button
          key={type}
          className={cn(
            'chip',
            active === type && 'active'
          )}
          onClick={() => onChange(active === type ? null : type)}
        >
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ background: entityColors[type] }}
          />
          {entityLabels[type]}s
        </button>
      ))}
    </div>
  )
}
