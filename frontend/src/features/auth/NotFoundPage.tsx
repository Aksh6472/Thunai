import { Link } from 'react-router'

import { useT } from '../../i18n/lang'

export function NotFoundPage() {
  const t = useT()
  return (
    <main className="mx-auto max-w-md space-y-4 p-8 text-center">
      <h1 className="text-2xl font-bold">{t('app.not_found')}</h1>
      <Link className="font-semibold text-primary underline" to="/login">
        {t('app.go_home')}
      </Link>
    </main>
  )
}
