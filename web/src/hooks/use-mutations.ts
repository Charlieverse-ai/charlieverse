import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export function useCreateEntity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { type: string; content: string; tags?: string[]; pinned?: boolean }) =>
      api.createEntity(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entities'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useUpdateEntity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; content?: string; tags?: string[]; pinned?: boolean }) =>
      api.updateEntity(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entities'] })
      qc.invalidateQueries({ queryKey: ['entity'] })
    },
  })
}

export function useDeleteEntity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteEntity(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entities'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function usePinEntity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, pinned }: { id: string; pinned: boolean }) =>
      api.pinEntity(id, pinned),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entities'] })
      qc.invalidateQueries({ queryKey: ['entity'] })
    },
  })
}

export function useCreateKnowledge() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { topic: string; content: string; tags?: string[]; pinned?: boolean }) =>
      api.createKnowledge(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useUpdateKnowledge() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; topic?: string; content?: string; tags?: string[]; pinned?: boolean }) =>
      api.updateKnowledge(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge'] })
    },
  })
}

export function useDeleteKnowledge() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteKnowledge(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function usePinKnowledge() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, pinned }: { id: string; pinned: boolean }) =>
      api.pinKnowledge(id, pinned),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['knowledge'] })
    },
  })
}
