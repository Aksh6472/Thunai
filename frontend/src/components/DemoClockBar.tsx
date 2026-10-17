import { useClock } from '../api/hooks/demo'
import { DEMO_MODE } from '../config/demo'
import { useT } from '../i18n/lang'
import { demoDay, formatIST } from '../lib/format'
import { Icon } from './Icon'

/** Simulated clock pill (demo mode only). */
export function DemoClockBar() {
  const t = useT()
  const clock = useClock(DEMO_MODE)
  if (!DEMO_MODE || !clock.data) return null
  const { sim_now, speed, running_scenario } = clock.data
  return (
    <div
      className="flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-sm shadow-[var(--shadow-card)]"
      aria-label={t('demo.clock')}
    >
      <Icon name="clock" className="h-4 w-4 text-primary" />
      <span className="font-semibold">{t('app.day', { n: demoDay(sim_now) })}</span>
      <span className="tabular-nums text-text-muted">{formatIST(sim_now)}</span>
      {speed > 0 && <span className="text-text-muted">{t('app.speed', { speed })}</span>}
      {running_scenario && (
        <span className="rounded-full bg-primary px-2 text-xs font-bold text-white">
          {t('demo.running', { id: running_scenario })}
        </span>
      )}
      <span className="rounded-full bg-simulated/10 px-2 text-[11px] font-bold tracking-wide text-simulated">
        {t('app.simulated')}
      </span>
    </div>
  )
}
