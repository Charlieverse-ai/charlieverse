import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useSessions(limit = 50) {
  return useQuery({
    queryKey: ['sessions', limit],
    queryFn: () => api.listSessions(limit),
    select: (data) => data,
  })
}

export function useSession(id: string | null) {
  return useQuery({
    queryKey: ['session', id],
    queryFn: () => api.getSession(id!),
    enabled: !!id,
  })
}
