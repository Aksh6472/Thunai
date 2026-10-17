import type { Lang } from '../api/types'
import { useT } from '../i18n/lang'

export function LanguageToggle({
  value,
  onChange,
  large = false,
}: {
  value: Lang
  onChange: (lang: Lang) => void
  large?: boolean
}) {
  const t = useT()
  const options: Lang[] = ['ta', 'en']
  return (
    <div
      role="group"
      aria-label={t('lang.label')}
      className="inline-flex overflow-hidden rounded-[var(--radius-control)] border border-border"
    >
      {options.map((lang) => (
        <button
          key={lang}
          type="button"
          lang={lang}
          aria-pressed={value === lang}
          onClick={() => onChange(lang)}
          className={`${large ? 'min-h-12 px-4 text-base' : 'min-h-9 px-3 text-sm'} font-semibold ${value === lang ? 'bg-primary text-white' : 'bg-surface text-text'}`}
        >
          {t(`lang.${lang}`)}
        </button>
      ))}
    </div>
  )
}
