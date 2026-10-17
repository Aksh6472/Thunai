import { useClock } from '../api/hooks/demo'
import { DEMO_MODE } from '../config/demo'
import { useT } from '../i18n/lang'
import { demoDay, formatIST } from '../lib/format'

export function DemoClockBar() {
  const t = useT()
  const clock = useClock(DEMO_MODE)
  if (!DEMO_MODE || !clock.data) return null
  const { sim_now, speed, running_scenario } = clock.data
  return (
    <div
      className="flex items-center gap-2 rounded-[var(--radius-control)] border border-simulated/40 bg-simulated/10 px-3 py-1 text-sm"
      aria-label={t('demo.clock')}
    >
      <span className="font-semibold">{t('app.day', { n: demoDay(sim_now) })}</span>
      <span className="tabular-nums">{formatIST(sim_now)}</span>
      {speed > 0 && <span className="text-text-muted">{t('app.speed', { speed })}</span>}
      {running_scenario && (
        <span className="rounded bg-simulated px-1.5 text-xs font-bold text-white">
          {t('demo.running', { id: running_scenario })}
        </span>
      )}
    </div>
  )
}
