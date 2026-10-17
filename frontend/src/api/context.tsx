// The API client is injected through context so component tests can use a fake (TESTING §4).
import { createContext, useContext, type ReactNode } from 'react'

import { createHttpClient, type ApiClient } from './client'

const defaultBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1'
const ApiContext = createContext<ApiClient>(createHttpClient(defaultBase))

export function ApiProvider({ client, children }: { client: ApiClient; children: ReactNode }) {
  return <ApiContext.Provider value={client}>{children}</ApiContext.Provider>
}

export function useApi(): ApiClient {
  return useContext(ApiContext)
}
