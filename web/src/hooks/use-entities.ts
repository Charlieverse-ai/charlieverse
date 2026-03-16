import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useEntities(type?: string) {
  return useQuery({
    queryKey: ['entities', type],
    queryFn: () => api.listEntities(type),
    select: (data) => data.entities,
  })
}

export function useEntity(id: string | null) {
  return useQuery({
    queryKey: ['entity', id],
    queryFn: () => api.getEntity(id!),
    enabled: !!id,
  })
}
