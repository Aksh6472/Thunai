import {
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { WatchPoint } from '../api/types'
import { useT } from '../i18n/lang'
import { demoDay, formatISTTime } from '../lib/format'

// Step line with tier bands; y axis always 0–100 (DESIGN §12). Text equivalent: the timeline.
const BANDS = [
  { y1: 0, y2: 30, color: 'var(--color-tier-low)' },
  { y1: 30, y2: 55, color: 'var(--color-tier-medium)' },
  { y1: 55, y2: 75, color: 'var(--color-tier-high)' },
  { y1: 75, y2: 100, color: 'var(--color-tier-very-high)' },
]

export function WatchScoreChart({
  history,
  height = 200,
  describedBy,
}: {
  history: WatchPoint[]
  height?: number
  describedBy?: string
}) {
  const t = useT()
  const data = history.map((p) => ({
    at: Date.parse(p.at),
    score: p.score,
    label: `${t('app.day', { n: demoDay(p.at) })} ${formatISTTime(p.at)}`,
  }))
  return (
    <figure aria-label={t('case.watch_chart')} aria-describedby={describedBy}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: -16 }}>
          {BANDS.map((b) => (
            <ReferenceArea
              key={b.y1}
              y1={b.y1}
              y2={b.y2}
              fill={b.color}
              fillOpacity={0.08}
              ifOverflow="hidden"
            />
          ))}
          {[30, 55, 75].map((y) => (
            <ReferenceLine
              key={y}
              y={y}
              stroke="var(--color-border)"
              strokeDasharray="4 4"
              label={{ value: String(y), position: 'right', fontSize: 11 }}
            />
          ))}
          <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
          <YAxis domain={[0, 100]} ticks={[0, 30, 55, 75, 100]} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v) => [String(v), t('ops.watch_score', { score: '' }).trim()]} />
          <Line
            type="stepAfter"
            dataKey="score"
            stroke="var(--color-primary)"
            strokeWidth={2}
            dot={{ r: 3 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </figure>
  )
}
