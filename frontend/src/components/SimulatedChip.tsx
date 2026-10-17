import { DEMO_MODE } from '../config/demo'
import { useT } from '../i18n/lang'

export function SimulatedChip() {
  const t = useT()
  if (!DEMO_MODE) return null
  return (
    <span className="inline-flex items-center rounded border border-simulated px-1.5 text-[11px] font-bold tracking-wide text-simulated">
      {t('app.simulated')}
    </span>
  )
}
