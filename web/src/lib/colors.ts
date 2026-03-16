import type { EntityType } from '../types'

export const entityColors: Record<EntityType, string> = {
  decision: '#F59E0B',
  solution: '#10B981',
  preference: '#EC4899',
  person: '#3B82F6',
  milestone: '#F97316',
  moment: '#8B5CF6',
}

export const entityLabels: Record<EntityType, string> = {
  decision: 'Decision',
  solution: 'Solution',
  preference: 'Preference',
  person: 'Person',
  milestone: 'Milestone',
  moment: 'Moment',
}
