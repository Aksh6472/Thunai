import { NavLink, Outlet } from 'react-router'

import type { Role } from '../api/types'
import { useAuth } from '../app/auth'
import { useT } from '../i18n/lang'
import { BrandMark } from './BrandMark'
import { DemoClockBar } from './DemoClockBar'
import { Icon, type IconName } from './Icon'

const LINKS: {
  to: string
  key: 'nav.ops' | 'nav.teller' | 'nav.demo'
  icon: IconName
  roles: Role[]
}[] = [
  { to: '/ops', key: 'nav.ops', icon: 'home', roles: ['OFFICER', 'ADMIN'] },
  { to: '/teller', key: 'nav.teller', icon: 'counter', roles: ['TELLER', 'OFFICER'] },
  { to: '/demo', key: 'nav.demo', icon: 'play', roles: ['ADMIN'] },
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
  const links = LINKS.filter((l) => user && l.roles.includes(user.role))
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[256px_1fr]">
      <aside className="sticky top-0 z-30 flex flex-col gap-6 border-b border-border bg-surface/90 px-4 py-4 backdrop-blur lg:h-screen lg:border-r lg:border-b-0 lg:px-5 lg:py-7">
        <div className="flex items-center justify-between gap-3 lg:block">
          <div className="px-1">
            <BrandMark tagline={t('nav.tagline')} />
          </div>
          <button
            type="button"
            onClick={logout}
            className="rounded-[var(--radius-control)] border border-border px-3 py-1.5 text-sm font-semibold lg:hidden"
          >
            {t('app.logout')}
          </button>
        </div>
        <nav aria-label={t('nav.main')} className="flex gap-1 lg:flex-col lg:gap-1.5">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `relative flex items-center gap-3 rounded-[14px] px-4 py-3 text-[15px] font-semibold transition-colors ${isActive ? 'bg-lilac text-primary before:absolute before:inset-y-2 before:-left-5 before:hidden before:w-1 before:rounded-r-full before:bg-primary before:content-[""] lg:before:block' : 'text-text-muted hover:bg-surface-2 hover:text-text'}`
              }
            >
              <Icon name={l.icon} />
              {t(l.key)}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto hidden space-y-4 lg:block">
          <div className="relative overflow-hidden rounded-[var(--radius-card)] bg-gradient-to-br from-accent to-primary p-5 text-white">
            <span
              aria-hidden="true"
              className="absolute -bottom-6 -right-6 h-24 w-24 rounded-full bg-white/15"
            />
            <span
              aria-hidden="true"
              className="absolute -right-2 bottom-8 h-10 w-10 rounded-full bg-white/20"
            />
            <p className="relative text-lg font-bold leading-snug">{t('nav.promo.title')}</p>
            <p className="relative mt-1 text-sm text-white/85">{t('nav.promo.body')}</p>
          </div>
          {user && (
            <div className="flex items-center gap-3 rounded-[var(--radius-card)] border border-border p-3">
              <span
                aria-hidden="true"
                className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-to-br from-lilac to-blush text-sm font-bold text-primary"
              >
                {initials(user.display_name)}
              </span>
              <span className="min-w-0 flex-1 leading-tight">
                <span className="block truncate text-sm font-semibold">{user.display_name}</span>
                <span className="block text-xs text-text-muted">{user.role}</span>
              </span>
              <button
                type="button"
                onClick={logout}
                aria-label={t('app.logout')}
                title={t('app.logout')}
                className="grid h-9 w-9 place-items-center rounded-full text-text-muted hover:bg-surface-2 hover:text-text"
              >
                <Icon name="logout" className="h-[18px] w-[18px]" />
              </button>
            </div>
          )}
        </div>
      </aside>
      <div className="min-w-0">
        <div className="flex items-center justify-end gap-3 px-4 pt-4 md:px-8">
          <DemoClockBar />
        </div>
        <Outlet />
      </div>
    </div>
  )
}
