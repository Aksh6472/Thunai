import type { Tier } from '../api/types'
import { useT } from '../i18n/lang'

// Text + icon + colour, never colour alone (DESIGN §6.2).
const ICON: Record<Tier, string> = { LOW: '●', MEDIUM: '▲', HIGH: '■', VERY_HIGH: '◆' }
const STYLE: Record<Tier, string> = {
  LOW: 'text-tier-low bg-tier-low/10 border-tier-low/40',
  MEDIUM: 'text-tier-medium bg-tier-medium/10 border-tier-medium/40',
  HIGH: 'text-tier-high bg-tier-high/10 border-tier-high/40',
  VERY_HIGH: 'text-tier-very-high bg-tier-very-high/10 border-tier-very-high border-2 font-bold',
}

export function TierBadge({ tier, size = 'md' }: { tier: Tier; size?: 'sm' | 'md' | 'lg' }) {
  const t = useT()
  const sizing =
    size === 'lg' ? 'text-base px-3 py-1' : size === 'sm' ? 'text-xs px-1.5' : 'text-sm px-2 py-0.5'
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border font-semibold ${STYLE[tier]} ${sizing}`}
    >
      <span aria-hidden="true">{ICON[tier]}</span>
      {t(`tier.${tier}`)}
    </span>
  )
}
