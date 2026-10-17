import type { ReactNode } from 'react'

/** 390×844 phone bezel on desktop; full-bleed below 768 px (DESIGN §11). */
export function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-start justify-center md:items-center md:py-8">
      <div className="relative flex w-full flex-col overflow-hidden bg-surface md:h-[844px] md:w-[390px] md:rounded-[var(--radius-phone)] md:border-[10px] md:border-text md:shadow-[0_10px_30px_rgb(0_0_0/0.2)]">
        <div className="flex-1 overflow-y-auto text-[18px]">{children}</div>
      </div>
    </div>
  )
}
