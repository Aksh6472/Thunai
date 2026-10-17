import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'

import { ApiProvider } from '../api/context'
import type { ApiClient } from '../api/client'
import { ToastProvider } from '../components/Toast'
import { LangProvider } from '../i18n/lang'
import { AuthProvider } from './auth'

export function makeQueryClient(): QueryClient {
  // Retry twice before showing an error state (DESIGN §9).
  return new QueryClient({ defaultOptions: { queries: { retry: 2 }, mutations: { retry: 0 } } })
}

export function Providers({ children, api }: { children: ReactNode; api?: ApiClient }) {
  const [queryClient] = useState(makeQueryClient)
  const tree = (
    <QueryClientProvider client={queryClient}>
      <LangProvider>
        <ToastProvider>
          <AuthProvider>{children}</AuthProvider>
        </ToastProvider>
      </LangProvider>
    </QueryClientProvider>
  )
  return api ? <ApiProvider client={api}>{tree}</ApiProvider> : tree
}
