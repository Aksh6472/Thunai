// Session handling and role guards (T-011). Roles and homes: DESIGN §3.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import { useApi } from '../api/context'
import { tokenStore, type Session } from '../api/tokenStore'
import type { LoginResponse, Role, User } from '../api/types'
import { ForbiddenPage } from '../features/auth/ForbiddenPage'

export const HOME: Record<Role, string> = {
  TELLER: '/teller',
  OFFICER: '/ops',
  ADMIN: '/demo',
  CUSTOMER: '/customer',
}

interface AuthState {
  user: User | null
  expired: boolean
  login: (username: string, password: string) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const api = useApi()
  const [session, setSession] = useState<Session | null>(tokenStore.session())
  const [expired, setExpired] = useState(false)

  useEffect(
    () =>
      tokenStore.subscribe((next, didExpire) => {
        setSession(next)
        if (didExpire) setExpired(true)
      }),
    [],
  )

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await api.post<LoginResponse>('/auth/login', { username, password })
      tokenStore.set({
        token: res.access_token,
        user: res.user,
        expiresAt: Date.now() + res.expires_in * 1000,
      })
      setExpired(false)
      return res.user
    },
    [api],
  )

  const logout = useCallback(() => tokenStore.set(null), [])

  return (
    <AuthContext.Provider value={{ user: session?.user ?? null, expired, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}

export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user } = useAuth()
  const location = useLocation()
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }
  if (!roles.includes(user.role)) return <ForbiddenPage />
  return <>{children}</>
}
