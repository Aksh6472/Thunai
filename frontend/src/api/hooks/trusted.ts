import { useMutation, useQuery } from '@tanstack/react-query'

import { ApiError } from '../client'
import { useApi } from '../context'
import type { ContactResponse, TrustedResponseOut, TrustedView } from '../types'

export function useTrustedView(token: string | undefined) {
  const api = useApi()
  return useQuery({
    queryKey: ['trusted', token],
    queryFn: () => api.get<TrustedView>(`/trusted/${token}`),
    enabled: Boolean(token),
    retry: (count, error) => !(error instanceof ApiError && error.status >= 400) && count < 2,
    refetchOnWindowFocus: false,
  })
}

export function useTrustedRespond(token: string) {
  const api = useApi()
  return useMutation({
    mutationFn: (response: ContactResponse) =>
      api.post<TrustedResponseOut>(`/trusted/${token}/response`, { response }),
  })
}
