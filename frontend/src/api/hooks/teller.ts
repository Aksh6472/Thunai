import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useApi } from '../context'
import type { AssessmentResult, HoldListItem, Lang, Page, ScriptOut } from '../types'
import { pollEvery } from './poll'

export type TellerItem = 'ON_CALL' | 'DISTRESSED' | 'FOLLOWING_INSTRUCTIONS' | 'MENTIONS_AUTHORITY'

export function useTellerQueue() {
  const api = useApi()
  return useQuery({
    queryKey: ['teller-queue'],
    queryFn: () => api.get<Page<HoldListItem>>('/teller/queue'),
    refetchInterval: pollEvery(),
  })
}

export function useChecklist(transferRef: string) {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { items: TellerItem[]; customer_said?: string }) =>
      api.post<AssessmentResult>(`/teller/transfers/${transferRef}/checklist`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['teller-queue'] })
      void qc.invalidateQueries({ queryKey: ['hold'] })
    },
  })
}

export function useScript(holdId: string | undefined, lang: Lang) {
  const api = useApi()
  return useQuery({
    queryKey: ['script', holdId, lang],
    queryFn: () => api.get<ScriptOut>(`/teller/holds/${holdId}/script?lang=${lang}`),
    enabled: Boolean(holdId),
    staleTime: 60_000,
  })
}
