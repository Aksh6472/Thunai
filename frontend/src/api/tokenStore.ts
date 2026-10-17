// Session token in memory plus sessionStorage (an accepted demo risk: SECURITY T-11).
import type { User } from './types'

const KEY = 'thunai.session'

export interface Session {
  token: string
  user: User
  expiresAt: number
}

type Listener = (session: Session | null, expired: boolean) => void

let current: Session | null = load()
const listeners = new Set<Listener>()

function load(): Session | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return null
    const session = JSON.parse(raw) as Session
    return session.expiresAt > Date.now() ? session : null
  } catch {
    return null
  }
}

function emit(expired = false) {
  listeners.forEach((l) => l(current, expired))
}

export const tokenStore = {
  get: () => current?.token ?? null,
  session: () => current,
  set(session: Session | null) {
    current = session
    try {
      if (session) sessionStorage.setItem(KEY, JSON.stringify(session))
      else sessionStorage.removeItem(KEY)
    } catch {
      /* storage unavailable: memory only */
    }
    emit()
  },
  expire() {
    if (!current) return
    current = null
    try {
      sessionStorage.removeItem(KEY)
    } catch {
      /* ignore */
    }
    emit(true)
  },
  subscribe(listener: Listener) {
    listeners.add(listener)
    return () => {
      listeners.delete(listener)
    }
  },
}
