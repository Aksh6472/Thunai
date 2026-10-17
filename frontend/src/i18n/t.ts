// Minimal i18n (TECH_STACK §3): two languages, flat keys, {placeholder} interpolation.
// Tamil strings are DRAFTS PENDING NATIVE REVIEW (DESIGN.md §6.3, T-038).
import { BANK_NAME, PRODUCT_NAME } from '../config/brand'
import en from './en.json'
import ta from './ta.json'

export type Lang = 'en' | 'ta'
export type MessageKey = keyof typeof en
export type Vars = Record<string, string | number>

const dictionaries: Record<Lang, Record<string, string>> = { en, ta }
const brand: Vars = { product: PRODUCT_NAME, bank: BANK_NAME }

export function t(key: MessageKey, lang: Lang = 'en', vars: Vars = {}): string {
  const template = dictionaries[lang][key] ?? en[key] ?? key
  const all = { ...brand, ...vars }
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in all ? String(all[name]) : match,
  )
}

export function hasKey(key: string): key is MessageKey {
  return key in en
}

export const dictionaryKeys = { en: Object.keys(en), ta: Object.keys(ta) }
