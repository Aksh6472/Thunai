import { PRODUCT_NAME } from '../config/brand'

/** Shield logo plus the product name. `tone` picks text colours for dark or light backgrounds. */
export function BrandMark({
  tone = 'dark',
  size = 'md',
}: {
  tone?: 'dark' | 'light'
  size?: 'md' | 'lg'
}) {
  const box = size === 'lg' ? 'h-10 w-10' : 'h-8 w-8'
  return (
    <span className="inline-flex items-center gap-2.5">
      <span
        aria-hidden="true"
        className={`grid ${box} place-items-center rounded-[10px] bg-gradient-to-br from-primary to-primary-strong shadow-sm`}
      >
        <svg viewBox="0 0 24 24" className="h-[60%] w-[60%]" fill="none">
          <path
            d="M12 2.5 4.5 5.5v6c0 4.6 3.1 8.6 7.5 10 4.4-1.4 7.5-5.4 7.5-10v-6L12 2.5Z"
            className="fill-white/15 stroke-white"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="m8.5 12 2.5 2.5 4.5-5"
            className="stroke-accent"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span
        className={`font-bold tracking-tight ${size === 'lg' ? 'text-2xl' : 'text-lg'} ${tone === 'dark' ? 'text-brand-text' : 'text-text'}`}
      >
        {PRODUCT_NAME}
      </span>
    </span>
  )
}
