import { Link } from 'react-router'

import { useAuth, HOME } from '../../app/auth'
import { useT } from '../../i18n/lang'

export function ForbiddenPage() {
  const t = useT()
  const { user } = useAuth()
  return (
    <main className="mx-auto max-w-md space-y-4 p-8 text-center">
      <h1 className="text-2xl font-bold">403</h1>
      <p>{t('app.forbidden')}</p>
      <Link className="font-semibold text-primary underline" to={user ? HOME[user.role] : '/login'}>
        {t('app.go_home')}
      </Link>
    </main>
  )
}
