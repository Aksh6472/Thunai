import { useClock } from '../api/hooks/demo'
import { DEMO_MODE } from '../config/demo'
import { useT } from '../i18n/lang'
import { demoDay, formatIST } from '../lib/format'

/** Simulated clock pill for the dark staff header. */
export function DemoClockBar() {
  const t = useT()
  const clock = useClock(DEMO_MODE)
  if (!DEMO_MODE || !clock.data) return null
  const { sim_now, speed, running_scenario } = clock.data
  return (
    <div
      className="flex items-center gap-2 rounded-full border border-white/15 bg-white/6 px-3 py-1 text-sm text-brand-text"
      aria-label={t('demo.clock')}
    >
      <span aria-hidden="true" className="h-2 w-2 rounded-full bg-accent" />
      <span className="font-semibold text-white">{t('app.day', { n: demoDay(sim_now) })}</span>
      <span className="tabular-nums">{formatIST(sim_now)}</span>
      {speed > 0 && <span className="text-brand-muted">{t('app.speed', { speed })}</span>}
      {running_scenario && (
        <span className="rounded-full bg-accent px-2 text-xs font-bold text-brand">
          {t('demo.running', { id: running_scenario })}
        </span>
      )}
    </div>
  )
}
