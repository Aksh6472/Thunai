import { PRODUCT_NAME } from '../config/brand'

/** Gradient shield logo, the product name and an optional tagline. */
export function BrandMark({ size = 'md', tagline }: { size?: 'md' | 'lg'; tagline?: string }) {
  const box = size === 'lg' ? 'h-12 w-12' : 'h-10 w-10'
  return (
    <span className="inline-flex items-center gap-3">
      <span
        aria-hidden="true"
        className={`grid ${box} shrink-0 place-items-center rounded-[14px] bg-gradient-to-br from-primary to-accent shadow-[0_8px_20px_rgb(108_76_245/0.35)]`}
      >
        <svg viewBox="0 0 24 24" className="h-[58%] w-[58%]" fill="none">
          <path
            d="M12 2.5 4.5 5.5v6c0 4.6 3.1 8.6 7.5 10 4.4-1.4 7.5-5.4 7.5-10v-6L12 2.5Z"
            className="fill-white/20 stroke-white"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="m8.5 12 2.5 2.5 4.5-5"
            className="stroke-white"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span className="leading-tight">
        <span
          className={`block font-extrabold uppercase tracking-wide text-brand ${size === 'lg' ? 'text-2xl' : 'text-xl'}`}
        >
          {PRODUCT_NAME}
        </span>
        {tagline && <span className="block text-sm text-text-muted">{tagline}</span>}
      </span>
    </span>
  )
}
