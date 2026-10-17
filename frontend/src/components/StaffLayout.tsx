import { NavLink, Outlet } from 'react-router'

import type { Role } from '../api/types'
import { useAuth } from '../app/auth'
import { PRODUCT_NAME } from '../config/brand'
import { useT } from '../i18n/lang'
import { Button } from './Button'
import { DemoClockBar } from './DemoClockBar'

const LINKS: { to: string; key: 'nav.ops' | 'nav.teller' | 'nav.demo'; roles: Role[] }[] = [
  { to: '/ops', key: 'nav.ops', roles: ['OFFICER', 'ADMIN'] },
  { to: '/teller', key: 'nav.teller', roles: ['TELLER', 'OFFICER'] },
  { to: '/demo', key: 'nav.demo', roles: ['ADMIN'] },
]

export function StaffLayout() {
  const t = useT()
  const { user, logout } = useAuth()
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-border bg-surface">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center gap-4 px-4 py-2">
          <span className="text-lg font-bold text-primary">{PRODUCT_NAME}</span>
          <nav aria-label={t('nav.main')} className="flex gap-1">
            {LINKS.filter((l) => user && l.roles.includes(user.role)).map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `rounded px-3 py-1.5 text-sm font-semibold ${isActive ? 'bg-primary/10 text-primary' : 'text-text-muted hover:text-text'}`
                }
              >
                {t(l.key)}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <DemoClockBar />
            {user && (
              <span className="text-sm">
                <span className="font-semibold">{user.display_name}</span>
                <span className="ml-1 text-text-muted">· {user.role}</span>
              </span>
            )}
            <Button size="sm" variant="secondary" onClick={logout}>
              {t('app.logout')}
            </Button>
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  )
}
