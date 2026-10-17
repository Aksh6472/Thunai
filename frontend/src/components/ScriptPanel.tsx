import type { Lang, ScriptOut } from '../api/types'
import { useT } from '../i18n/lang'

export function ScriptPanel({ script, lang }: { script: ScriptOut; lang: Lang }) {
  const t = useT()
  return (
    <div>
      {lang === 'ta' && !script.reviewed_by_native_speaker && (
        <p className="mb-2 rounded border border-tier-medium/50 bg-tier-medium/10 px-2 py-1 text-xs font-semibold text-tier-medium">
          {t('teller.script_unreviewed')}
        </p>
      )}
      <ol className="space-y-3" lang={lang}>
        {script.steps.map((step, i) =>
          step.id === 'do_not' ? (
            <li
              key={step.id}
              className="rounded border-l-4 border-tier-very-high bg-tier-very-high/10 p-2 text-sm"
            >
              <span aria-hidden="true">✗ </span>
              {step.text}
            </li>
          ) : (
            <li key={step.id} className="flex gap-2 text-sm leading-relaxed">
              <span className="font-bold text-primary">{i + 1}.</span>
              <span>{step.text}</span>
            </li>
          ),
        )}
      </ol>
    </div>
  )
}
