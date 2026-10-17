import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useApi } from '../context'
import type {
  CustomerOverview,
  CustomerTransferIn,
  CustomerTransferOut,
  TransferStatusOut,
} from '../types'
import { pollEvery } from './poll'

export function useOverview() {
  const api = useApi()
  return useQuery({
    queryKey: ['overview'],
    queryFn: () => api.get<CustomerOverview>('/customer/overview'),
    refetchInterval: pollEvery(5000),
  })
}

export function useCreateTransfer() {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CustomerTransferIn) =>
      api.post<CustomerTransferOut>('/customer/transfers', body),
    onSuccess: (out) => {
      qc.setQueryData(['customer-transfer', out.transfer_ref], out)
      void qc.invalidateQueries({ queryKey: ['overview'] })
    },
  })
}

/** Polls every 2 s while the transfer is held or warned (DESIGN §5.6). */
export function useTransferStatus(ref: string | null) {
  const api = useApi()
  return useQuery({
    queryKey: ['customer-transfer', ref],
    queryFn: () => api.get<CustomerTransferOut>(`/customer/transfers/${ref}`),
    enabled: Boolean(ref),
    refetchInterval: (query) => {
      const status = query.state.data?.transfer_status
      return status === 'HELD' || status === 'WARNED' ? pollEvery()(query) : false
    },
  })
}

export function useWarningResponse(ref: string) {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (action: 'CONTINUE' | 'CANCEL') =>
      api.post<TransferStatusOut>(`/customer/transfers/${ref}/warning-response`, { action }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['customer-transfer', ref] })
      void qc.invalidateQueries({ queryKey: ['overview'] })
    },
  })
}

export function useCancelHeld(ref: string) {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<TransferStatusOut>(`/customer/transfers/${ref}/cancel`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['customer-transfer', ref] })
      void qc.invalidateQueries({ queryKey: ['overview'] })
    },
  })
}

export function useConsent() {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      consent_type: 'CALL_SIGNAL' | 'TRUSTED_CONTACT_SHARING'
      granted: boolean
      text_version: string
    }) => api.post('/customer/consents', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['overview'] }),
  })
}

export function useRegisterContact() {
  const api = useApi()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      display_name: string
      relationship: string
      phone_e164: string
      preferred_language: 'en' | 'ta'
    }) => api.post<{ status: string; effective_from: string }>('/customer/trusted-contact', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['overview'] }),
  })
}
