import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useStories(tier?: string) {
  return useQuery({
    queryKey: ['stories', tier],
    queryFn: async () => {
      const res = await api.listStories(tier)
      return res.stories
    },
  })
}

export function useStory(id: string | null) {
  return useQuery({
    queryKey: ['story', id],
    queryFn: () => api.getStory(id!),
    enabled: !!id,
  })
}
