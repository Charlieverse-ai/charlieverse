const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  // Entities (memories)
  listEntities: (type?: string, limit = 100) => {
    const params = new URLSearchParams()
    if (type) params.set('type', type)
    params.set('limit', String(limit))
    return request<{ entities: import('../types').Entity[] }>(`/entities?${params}`)
  },

  getEntity: (id: string) =>
    request<import('../types').Entity>(`/entities/${id}`),

  // Sessions
  listSessions: (limit = 50) =>
    request<{ sessions: import('../types').Session[] }>(`/sessions/list?limit=${limit}`),

  getSession: (id: string) =>
    request<import('../types').Session>(`/sessions/${id}`),

  // Knowledge
  listKnowledge: (limit = 50) =>
    request<{ articles: import('../types').Knowledge[] }>(`/knowledge?limit=${limit}`),

  getKnowledge: (id: string) =>
    request<import('../types').Knowledge>(`/knowledge/${id}`),

  // Search
  search: (query: string, limit = 10) =>
    request<{ entities: import('../types').Entity[]; knowledge: import('../types').Knowledge[] }>(
      '/search',
      { method: 'POST', body: JSON.stringify({ query, limit }) },
    ),

  // Stories
  listStories: (tier?: string, limit = 50) => {
    const params = new URLSearchParams()
    if (tier) params.set('tier', tier)
    params.set('limit', String(limit))
    return request<{ stories: import('../types').Story[] }>(`/stories?${params}`)
  },

  getStory: (id: string) =>
    request<import('../types').Story>(`/stories/${id}`),

  // Stats
  stats: () => request<import('../types').Stats>('/stats'),

  // Health
  health: () => request<{ status: string }>('/health'),
}
