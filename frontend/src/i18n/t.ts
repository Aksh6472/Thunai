// Minimal i18n (TECH_STACK §3): two languages, flat keys, {placeholder} interpolation.
// Tamil strings are PENDING NATIVE REVIEW (DESIGN.md §6.3, T-038).
import en from './en.json'
import ta from './ta.json'

export type Lang = 'en' | 'ta'
export type MessageKey = keyof typeof en

const dictionaries: Record<Lang, Record<string, string>> = { en, ta }

export function t(key: MessageKey, lang: Lang = 'en', vars: Record<string, string> = {}): string {
  const template = dictionaries[lang][key] ?? en[key]
  return template.replace(/\{(\w+)\}/g, (match, name: string) => vars[name] ?? match)
}

export const dictionaryKeys = { en: Object.keys(en), ta: Object.keys(ta) }
