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
  listEntities: (type?: string, limit = 1000) => {
    const params = new URLSearchParams()
    if (type) params.set('type', type)
    params.set('limit', String(limit))
    return request<import('../types').Entity[]>(`/memories?${params}`)
  },

  getEntity: (id: string) =>
    request<import('../types').Entity>(`/memories/${id}`),

  // Sessions
  listSessions: (limit = 50) =>
    request<import('../types').Session[]>(`/sessions/list?limit=${limit}`),

  getSession: (id: string) =>
    request<import('../types').Session>(`/sessions/${id}`),

  // Knowledge
  listKnowledge: (limit = 50) =>
    request<import('../types').Knowledge[]>(`/knowledge?limit=${limit}`),

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
    return request<import('../types').Story[]>(`/stories?${params}`)
  },

  getStory: (id: string) =>
    request<import('../types').Story>(`/stories/${id}`),

  // Stats
  stats: () => request<import('../types').Stats>('/stats'),

  // Mutations — Entities
  createEntity: (data: { type: string; content: string; tags?: string[]; pinned?: boolean }) =>
    request<import('../types').Entity>('/memories', { method: 'POST', body: JSON.stringify(data) }),

  updateEntity: (id: string, data: { content?: string; tags?: string[]; pinned?: boolean }) =>
    request<import('../types').Entity>(`/memories/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  deleteEntity: (id: string) =>
    request<{ deleted: boolean }>(`/memories/${id}`, { method: 'DELETE' }),

  pinEntity: (id: string, pinned: boolean) =>
    request<import('../types').Entity>(`/memories/${id}/pin`, { method: 'POST', body: JSON.stringify({ pinned }) }),

  // Mutations — Knowledge
  createKnowledge: (data: { topic: string; content: string; tags?: string[]; pinned?: boolean }) =>
    request<import('../types').Knowledge>('/knowledge', { method: 'POST', body: JSON.stringify(data) }),

  updateKnowledge: (id: string, data: { topic?: string; content?: string; tags?: string[]; pinned?: boolean }) =>
    request<import('../types').Knowledge>(`/knowledge/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  deleteKnowledge: (id: string) =>
    request<{ deleted: boolean }>(`/knowledge/${id}`, { method: 'DELETE' }),

  pinKnowledge: (id: string, pinned: boolean) =>
    request<import('../types').Knowledge>(`/knowledge/${id}/pin`, { method: 'POST', body: JSON.stringify({ pinned }) }),

  // Health
  health: () => request<{ status: string }>('/health'),

  // Maintenance
  rebuild: () => request<{ status: string }>('/rebuild', { method: 'POST' }),
}
