import { NavLink, Outlet } from 'react-router'

import type { Role } from '../api/types'
import { useAuth } from '../app/auth'
import { useT } from '../i18n/lang'
import { BrandMark } from './BrandMark'
import { DemoClockBar } from './DemoClockBar'

const LINKS: { to: string; key: 'nav.ops' | 'nav.teller' | 'nav.demo'; roles: Role[] }[] = [
  { to: '/ops', key: 'nav.ops', roles: ['OFFICER', 'ADMIN'] },
  { to: '/teller', key: 'nav.teller', roles: ['TELLER', 'OFFICER'] },
  { to: '/demo', key: 'nav.demo', roles: ['ADMIN'] },
]

function initials(name: string): string {
  return name
    .replace(/\(.*?\)/g, '')
    .split(/[\s.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('')
}

export function StaffLayout() {
  const t = useT()
  const { user, logout } = useAuth()
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 bg-brand text-brand-text shadow-[0_1px_0_rgb(255_255_255/0.06)]">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5">
          <BrandMark />
          <nav aria-label={t('nav.main')} className="flex gap-1">
            {LINKS.filter((l) => user && l.roles.includes(user.role)).map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `rounded-[var(--radius-control)] px-3 py-1.5 text-sm font-semibold transition-colors ${isActive ? 'bg-white/12 text-white' : 'text-brand-muted hover:bg-white/6 hover:text-white'}`
                }
              >
                {t(l.key)}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <DemoClockBar />
            {user && (
              <span className="flex items-center gap-2 text-sm">
                <span
                  aria-hidden="true"
                  className="grid h-8 w-8 place-items-center rounded-full bg-brand-2 text-xs font-bold text-accent ring-1 ring-white/10"
                >
                  {initials(user.display_name)}
                </span>
                <span className="leading-tight">
                  <span className="block font-semibold text-white">{user.display_name}</span>
                  <span className="block text-xs text-brand-muted">{user.role}</span>
                </span>
              </span>
            )}
            <button
              type="button"
              onClick={logout}
              className="min-h-9 rounded-[var(--radius-control)] border border-white/15 px-3 text-sm font-semibold text-brand-text hover:bg-white/8"
            >
              {t('app.logout')}
            </button>
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  )
}
