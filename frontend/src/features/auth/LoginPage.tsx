import { useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'

import { ApiError } from '../../api/client'
import { HOME, useAuth } from '../../app/auth'
import { PRODUCT_NAME } from '../../config/brand'
import { DEMO_MODE } from '../../config/demo'
import { Button } from '../../components/Button'
import { Field, inputClass } from '../../components/Field'
import { ErrorBanner } from '../../components/States'
import { useT } from '../../i18n/lang'

const DEMO_USERS = [
  'teller.priya',
  'officer.rao',
  'admin.demo',
  'cust.kamala',
  'cust.iqbal',
  'cust.meena',
]

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
    <main className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={submit}
        noValidate
        className="w-full max-w-[400px] space-y-4 rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-[0_1px_2px_rgb(0_0_0/0.06)]"
      >
        <p className="text-2xl font-bold text-primary">{PRODUCT_NAME}</p>
        <h1 className="text-xl font-semibold">{t('login.title')}</h1>
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
        <Button type="submit" className="w-full" loading={busy}>
          {t('login.submit')}
        </Button>
        {DEMO_MODE && (
          <div className="rounded bg-bg p-3 text-sm">
            <p className="font-semibold">{t('login.demo_accounts')}</p>
            <ul className="mt-1 flex flex-wrap gap-2">
              {DEMO_USERS.map((u) => (
                <li key={u}>
                  <button
                    type="button"
                    className="font-mono text-primary underline"
                    onClick={() => setUsername(u)}
                  >
                    {u}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </form>
    </main>
  )
}
