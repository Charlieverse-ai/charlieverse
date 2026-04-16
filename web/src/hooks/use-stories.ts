import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useStories(tier?: string) {
  return useQuery({
    queryKey: ['stories', tier],
    queryFn: () => api.listStories(tier),
  })
}

/** Stories of a given tier whose period overlaps [periodStart, periodEnd]. */
export function useStoriesInPeriod(
  tier: string | undefined,
  periodStart: string | null,
  periodEnd: string | null,
) {
  return useQuery({
    queryKey: ['stories', tier, 'period', periodStart, periodEnd],
    queryFn: () =>
      api.listStories(tier, {
        periodStart: periodStart!,
        periodEnd: periodEnd!,
      }),
    enabled: !!periodStart && !!periodEnd,
  })
}

export function useStory(id: string | null) {
  return useQuery({
    queryKey: ['story', id],
    queryFn: () => api.getStory(id!),
    enabled: !!id,
  })
}
