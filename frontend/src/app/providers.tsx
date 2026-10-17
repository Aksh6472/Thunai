import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'

export function Providers({ children }: { children: ReactNode }) {
  // One client per app instance; retry twice before showing an error state (DESIGN §9).
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 2 } } }),
  )
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
