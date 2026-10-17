/** Decorative hero art: a soft shield with a tick, orbiting coins and a pause badge. */
export function ShieldIllustration({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 320 220" aria-hidden="true" className={className} fill="none">
      <circle cx="170" cy="110" r="96" className="fill-white/50" />
      <circle cx="170" cy="110" r="70" className="fill-white/60" />
      <path
        d="M170 40 118 60v40c0 33 22 62 52 74 30-12 52-41 52-74V60l-52-20Z"
        className="fill-primary/15 stroke-primary"
        strokeWidth="4"
        strokeLinejoin="round"
      />
      <path
        d="M170 56 132 71v29c0 24 16 45 38 54 22-9 38-30 38-54V71l-38-15Z"
        className="fill-white"
      />
      <path
        d="m150 104 14 14 26-28"
        className="stroke-primary"
        strokeWidth="8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <g>
        <circle cx="268" cy="62" r="22" className="fill-accent/30" />
        <circle cx="268" cy="62" r="15" className="fill-white" />
        <path
          d="M262 56h12M262 61h12M265 56c6 0 6 9 0 9h-3l8 6"
          className="stroke-primary"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
      <g>
        <circle cx="66" cy="150" r="24" className="fill-white" />
        <rect x="57" y="140" width="6" height="20" rx="2" className="fill-primary" />
        <rect x="69" y="140" width="6" height="20" rx="2" className="fill-primary" />
      </g>
      <circle cx="90" cy="58" r="7" className="fill-accent/50" />
      <circle cx="250" cy="170" r="10" className="fill-primary/20" />
      <circle cx="40" cy="96" r="4" className="fill-primary/30" />
    </svg>
  )
}
