import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

interface ToastItem {
  id: number
  text: string
  tone: 'success' | 'error' | 'info'
}

const ToastContext = createContext<(text: string, tone?: ToastItem['tone']) => void>(
  () => undefined,
)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const push = useCallback((text: string, tone: ToastItem['tone'] = 'success') => {
    const id = Date.now() + Math.random()
    setItems((list) => [...list, { id, text, tone }])
    setTimeout(() => setItems((list) => list.filter((i) => i.id !== id)), 4000)
  }, [])
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2"
      >
        {items.map((i) => (
          <div
            key={i.id}
            className={`pointer-events-auto rounded-[var(--radius-card)] px-4 py-3 text-sm font-semibold text-white shadow-[0_10px_30px_rgb(0_0_0/0.2)] ${i.tone === 'error' ? 'bg-tier-very-high' : i.tone === 'info' ? 'bg-primary' : 'bg-success'}`}
          >
            {i.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
