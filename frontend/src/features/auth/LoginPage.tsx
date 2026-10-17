import { useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'

import { ApiError } from '../../api/client'
import { HOME, useAuth } from '../../app/auth'
import { BANK_NAME } from '../../config/brand'
import { DEMO_MODE } from '../../config/demo'
import { BrandMark } from '../../components/BrandMark'
import { Button } from '../../components/Button'
import { Field, inputClass } from '../../components/Field'
import { ErrorBanner } from '../../components/States'
import { useT } from '../../i18n/lang'

type RoleKey =
  'login.role.teller' | 'login.role.officer' | 'login.role.admin' | 'login.role.customer'

const DEMO_USERS: { username: string; role: RoleKey }[] = [
  { username: 'officer.rao', role: 'login.role.officer' },
  { username: 'teller.priya', role: 'login.role.teller' },
  { username: 'admin.demo', role: 'login.role.admin' },
  { username: 'cust.kamala', role: 'login.role.customer' },
  { username: 'cust.iqbal', role: 'login.role.customer' },
  { username: 'cust.meena', role: 'login.role.customer' },
]

const POINTS = ['login.point.sequence', 'login.point.explained', 'login.point.gentle'] as const

export function LoginPage() {
  const t = useT()
  const { user, login, expired } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const next = params.get('next')
  if (user && !busy) return <Navigate to={HOME[user.role]} replace />

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!username || !password) {
      setError(t('login.required'))
      return
    }
    setBusy(true)
    setError(null)
    try {
      const u = await login(username.trim(), password)
      navigate(next && next.startsWith('/') && !next.startsWith('//') ? next : HOME[u.role], {
        replace: true,
      })
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 429 ? t('login.rate_limited') : t('login.error'),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative hidden overflow-hidden bg-brand p-12 text-brand-text lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-32 -top-32 h-[480px] w-[480px] rounded-full bg-primary/25 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-40 -left-24 h-[420px] w-[420px] rounded-full bg-accent/10 blur-3xl"
        />
        <BrandMark size="lg" />
        <div className="relative max-w-[520px] space-y-8">
          <h2 className="text-4xl font-bold leading-tight text-white">{t('login.tagline')}</h2>
          <ul className="space-y-4">
            {POINTS.map((k) => (
              <li key={k} className="flex gap-3 text-base">
                <span
                  aria-hidden="true"
                  className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent/15 text-sm font-bold text-accent"
                >
                  ✓
                </span>
                <span>{t(k)}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-sm text-brand-muted">
          {t('login.footer', { bank: BANK_NAME })}
        </p>
      </aside>

      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} noValidate className="w-full max-w-[420px] space-y-5">
          <div className="lg:hidden">
            <BrandMark tone="light" />
          </div>
          <div className="space-y-1">
            <h1 className="text-2xl font-bold tracking-tight">{t('login.title')}</h1>
            <p className="text-text-muted">{t('login.subtitle')}</p>
          </div>
          {expired && !error && <ErrorBanner message={t('login.expired')} />}
          {error && <ErrorBanner message={error} />}
          <Field label={t('login.username')}>
            {(p) => (
              <input
                id={p.id}
                className={inputClass}
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            )}
          </Field>
          <Field label={t('login.password')}>
            {(p) => (
              <input
                id={p.id}
                type="password"
                className={inputClass}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            )}
          </Field>
          <Button type="submit" size="lg" className="w-full" loading={busy}>
            {t('login.submit')}
          </Button>
          {DEMO_MODE && (
            <div className="space-y-2 rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-[var(--shadow-card)]">
              <p className="text-sm font-semibold">{t('login.demo_accounts')}</p>
              <ul className="grid grid-cols-2 gap-2">
                {DEMO_USERS.map((u) => (
                  <li key={u.username}>
                    <button
                      type="button"
                      aria-pressed={username === u.username}
                      className={`w-full rounded-[var(--radius-control)] border px-3 py-2 text-left transition-colors ${username === u.username ? 'border-primary bg-primary/10' : 'border-border hover:bg-surface-2'}`}
                      onClick={() => setUsername(u.username)}
                    >
                      <span className="block font-mono text-sm font-semibold text-primary">
                        {u.username}
                      </span>
                      <span className="block text-xs text-text-muted">{t(u.role)}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-text-muted">{t('login.demo_password_hint')}</p>
            </div>
          )}
        </form>
      </div>
    </main>
  )
}
