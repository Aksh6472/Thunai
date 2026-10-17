import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

import { t, type Lang, type MessageKey, type Vars } from './t'

interface LangState {
  lang: Lang
  setLang: (lang: Lang) => void
}

const LangContext = createContext<LangState>({ lang: 'en', setLang: () => undefined })

export function LangProvider({
  initial = 'en',
  children,
}: {
  initial?: Lang
  children: ReactNode
}) {
  const [lang, setLang] = useState<Lang>(initial)
  const value = useMemo(() => ({ lang, setLang }), [lang])
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>
}

export function useLang(): LangState {
  return useContext(LangContext)
}

/** Translate in the current language. */
export function useT(): (key: MessageKey, vars?: Vars) => string {
  const { lang } = useLang()
  return useCallback((key: MessageKey, vars?: Vars) => t(key, lang, vars), [lang])
}
