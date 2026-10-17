import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useApi } from '../context'
import type {
  AlertItem,
  CustomerRisk,
  HoldDetail,
  OfficerDecisionIn,
  Page,
  Summary,
  TimelineItem,
} from '../types'
import { pollEvery } from './poll'

export type AlertKind = 'HOLD' | 'WARN' | 'WATCH'

export function useSummary() {
  const api = useApi()
  return useQuery({
    queryKey: ['summary'],
    queryFn: () => api.get<Summary>('/dashboard/summary'),
    refetchInterval: pollEvery(),
  })
}

export function useAlerts(kind?: AlertKind) {
  const api = useApi()
  return useQuery({
    queryKey: ['alerts', kind ?? 'ALL'],
    queryFn: () => api.get<Page<AlertItem>>(`/alerts?limit=100${kind ? `&kind=${kind}` : ''}`),
    refetchInterval: pollEvery(),
  })
}

export function useHold(holdId: string | undefined) {
  const api = useApi()
  return useQuery({
    queryKey: ['hold', holdId],
    queryFn: () => api.get<HoldDetail>(`/holds/${holdId}`),
    enabled: Boolean(holdId),
    refetchInterval: pollEvery(),
  })
}

export function useOfficerDecision(holdId: string) {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: OfficerDecisionIn) =>
      api.post<HoldDetail>(`/holds/${holdId}/officer-decision`, body),
    onSuccess: (detail) => {
      qc.setQueryData(['hold', holdId], detail)
      void qc.invalidateQueries({ queryKey: ['alerts'] })
      void qc.invalidateQueries({ queryKey: ['summary'] })
    },
  })
}

export function useResendContact(holdId: string) {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post(`/holds/${holdId}/resend-contact`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hold', holdId] }),
  })
}

export function useCustomerRisk(customerId: string | undefined) {
  const api = useApi()
  return useQuery({
    queryKey: ['customer-risk', customerId],
    queryFn: () => api.get<CustomerRisk>(`/customers/${customerId}/risk`),
    enabled: Boolean(customerId),
    refetchInterval: pollEvery(5000),
  })
}

export function useTimeline(customerId: string | undefined, days = 14) {
  const api = useApi()
  return useQuery({
    queryKey: ['timeline', customerId, days],
    queryFn: () => api.get<TimelineItem[]>(`/customers/${customerId}/timeline?days=${days}`),
    enabled: Boolean(customerId),
    refetchInterval: pollEvery(5000),
  })
}
