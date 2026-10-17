import { PRODUCT_NAME } from '../../config/brand'
import { t, type MessageKey } from '../../i18n/t'

// Temporary screen until each surface is built (T-011, T-033–T-039).
export function Placeholder({ screen }: { screen: MessageKey }) {
  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">
        {t('app.placeholder', 'en', { product: PRODUCT_NAME, screen: t(screen) })}
      </h1>
    </main>
  )
}
