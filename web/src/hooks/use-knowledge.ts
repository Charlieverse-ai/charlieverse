import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useKnowledge(limit = 50) {
  return useQuery({
    queryKey: ['knowledge', limit],
    queryFn: () => api.listKnowledge(limit),
    select: (data) => data.articles,
  })
}

export function useKnowledgeArticle(id: string | null) {
  return useQuery({
    queryKey: ['knowledge', id],
    queryFn: () => api.getKnowledge(id!),
    enabled: !!id,
  })
}
