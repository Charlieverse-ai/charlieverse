export type EntityType = 'decision' | 'solution' | 'preference' | 'person' | 'milestone' | 'moment'

export interface Entity {
  id: string
  type: EntityType
  content: string
  tags: string[] | null
  pinned: boolean
  created_session_id: string
  created_at: string
  updated_at: string
}

export interface Session {
  id: string
  what_happened: string | null
  for_next_session: string | null
  tags: string[] | null
  workspace: string | null
  created_at: string
  updated_at: string
}

export interface Knowledge {
  id: string
  topic: string
  content: string
  tags: string[] | null
  pinned: boolean
  created_at: string
  updated_at: string
}

export type StoryTier = 'session' | 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly' | 'all-time'

export interface Story {
  id: string
  title: string
  content: string
  tier: StoryTier
  period_start: string | null
  period_end: string | null
  tags: string[] | null
  created_at: string
  updated_at: string
}

export interface Stats {
  entities: Record<EntityType, number>
  sessions: number
  knowledge: number
}
