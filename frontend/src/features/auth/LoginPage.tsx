import { useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'

import { ApiError } from '../../api/client'
import { HOME, useAuth } from '../../app/auth'
import { BANK_NAME } from '../../config/brand'
import { DEMO_AUTOFILL_PASSWORD, DEMO_MODE } from '../../config/demo'
import { BrandMark } from '../../components/BrandMark'
import { ShieldIllustration } from '../../components/ShieldIllustration'
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
      <aside className="relative m-4 hidden overflow-hidden rounded-[32px] bg-gradient-to-br from-lilac via-surface-2 to-blush p-12 lg:flex lg:flex-col lg:justify-between">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-24 h-[380px] w-[380px] rounded-full bg-accent/25 blur-3xl"
        />
        <BrandMark size="lg" tagline={t('nav.tagline')} />
        <div className="relative max-w-[540px] space-y-8">
          <ShieldIllustration className="h-[190px] w-auto" />
          <h2 className="text-[40px] font-extrabold leading-tight tracking-tight text-brand">
            {t('login.tagline')}{' '}
            <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              {t('login.tagline_accent')}
            </span>
          </h2>
          <ul className="space-y-4">
            {POINTS.map((k) => (
              <li key={k} className="flex gap-3 text-base text-text-muted">
                <span
                  aria-hidden="true"
                  className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-surface text-sm font-bold text-primary shadow-sm"
                >
                  ✓
                </span>
                <span>{t(k)}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-sm text-text-muted">{t('login.footer', { bank: BANK_NAME })}</p>
      </aside>

      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} noValidate className="w-full max-w-[420px] space-y-5">
          <div className="lg:hidden">
            <BrandMark />
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
            <div className="space-y-3 rounded-[var(--radius-card)] bg-surface p-5 shadow-[var(--shadow-card)]">
              <p className="text-sm font-semibold">{t('login.demo_accounts')}</p>
              <ul className="grid grid-cols-2 gap-2">
                {DEMO_USERS.map((u) => (
                  <li key={u.username}>
                    <button
                      type="button"
                      aria-pressed={username === u.username}
                      className={`w-full rounded-[14px] border px-3 py-2.5 text-left transition-colors ${username === u.username ? 'border-primary bg-lilac' : 'border-border hover:bg-surface-2'}`}
                      onClick={() => {
                        setUsername(u.username)
                        if (DEMO_AUTOFILL_PASSWORD) setPassword(DEMO_AUTOFILL_PASSWORD)
                      }}
                    >
                      <span className="block font-mono text-sm font-semibold text-primary">
                        {u.username}
                      </span>
                      <span className="block text-xs text-text-muted">{t(u.role)}</span>
                    </button>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-text-muted">
                {t(
                  DEMO_AUTOFILL_PASSWORD ? 'login.demo_autofill_hint' : 'login.demo_password_hint',
                )}
              </p>
            </div>
          )}
        </form>
      </div>
    </main>
  )
}
