import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useApi } from '../context'
import type { ReportOut, ReportPatchIn } from '../types'

export function useCreateReport(holdId: string) {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<ReportOut>(`/holds/${holdId}/report`, { use_llm: false }),
    onSuccess: (report) => {
      qc.setQueryData(['report', report.id], report)
      void qc.invalidateQueries({ queryKey: ['hold', holdId] })
    },
  })
}

export function useReport(reportId: string | null | undefined) {
  const api = useApi()
  return useQuery({
    queryKey: ['report', reportId],
    queryFn: () => api.get<ReportOut>(`/reports/${reportId}`),
    enabled: Boolean(reportId),
  })
}

export function usePatchReport(reportId: string) {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReportPatchIn) => api.patch<ReportOut>(`/reports/${reportId}`, body),
    onSuccess: (report) => qc.setQueryData(['report', reportId], report),
  })
}

export function useMarkFiled(reportId: string) {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ack: string) =>
      api.post<ReportOut>(`/reports/${reportId}/mark-filed`, { acknowledgement_number: ack }),
    onSuccess: (report) => qc.setQueryData(['report', reportId], report),
  })
}
