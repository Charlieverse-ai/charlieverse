import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useSearch(query: string) {
  return useQuery({
    queryKey: ['search', query],
    queryFn: () => api.search(query),
    enabled: query.length > 1,
    placeholderData: (prev) => prev,
  })
}

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: () => api.stats(),
  })
}
