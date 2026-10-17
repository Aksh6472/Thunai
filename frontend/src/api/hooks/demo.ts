import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useApi } from '../context'
import type { ClockOut, ConsoleMessage, RunOut, ScenarioOut } from '../types'
import { pollEvery } from './poll'

export function useClock(enabled = true) {
  const api = useApi()
  return useQuery({
    queryKey: ['demo-clock'],
    queryFn: () => api.get<ClockOut>('/demo/clock'),
    enabled,
    refetchInterval: pollEvery(1000),
  })
}

export function useScenarios() {
  const api = useApi()
  return useQuery({
    queryKey: ['scenarios'],
    queryFn: () => api.get<ScenarioOut[]>('/demo/scenarios'),
  })
}

export function useRuns() {
  const api = useApi()
  return useQuery({
    queryKey: ['demo-runs'],
    queryFn: () => api.get<RunOut[]>('/demo/runs?limit=10'),
    refetchInterval: pollEvery(1000),
  })
}

export function useConsoleMessages() {
  const api = useApi()
  return useQuery({
    queryKey: ['console-messages'],
    queryFn: () => api.get<ConsoleMessage[]>('/demo/console-messages?limit=10'),
    refetchInterval: pollEvery(),
  })
}

export function useResetDemo() {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<{ seconds: number; customers: number }>('/demo/reset'),
    onSuccess: () => qc.invalidateQueries(),
  })
}

export function useRunScenario() {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, speed }: { id: string; speed: number }) =>
      api.post<RunOut>(`/demo/scenarios/${id}/run`, { speed }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['demo-runs'] }),
  })
}

export function useSetFri() {
  const api = useApi()
  return useMutation({
    mutationFn: (body: { linked_msisdn: string; rating: 'MEDIUM' | 'HIGH' | 'VERY_HIGH' }) =>
      api.post<{ rating: string }>('/demo/fri', body),
  })
}
