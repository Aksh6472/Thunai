// Formatting at the edges only (ADR-009): money arrives as integer paise, times as ISO UTC.
const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})
const grouping = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })
const istDateTime = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Kolkata',
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})
const istTime = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Kolkata',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})
const istDay = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' })

/** 460000000 → "₹46,00,000" */
export function formatINR(paise: number): string {
  return inr.format(Math.round(paise / 100))
}

/** 4600000 → "46,00,000" (for amount inputs) */
export function groupRupees(rupees: number): string {
  return grouping.format(rupees)
}

/** "46,00,000" or "₹ 4600000" → 4600000; null if not a positive whole number of rupees. */
export function parseRupees(input: string): number | null {
  const cleaned = input.replace(/[₹,\s]/g, '')
  if (!/^\d{1,11}$/.test(cleaned)) return null
  const value = Number(cleaned)
  return value > 0 ? value : null
}

/** ISO → "03 Oct, 11:20" in IST */
export function formatIST(iso: string): string {
  return istDateTime.format(new Date(iso))
}

export function formatISTTime(iso: string): string {
  return istTime.format(new Date(iso))
}

const DEMO_DAY_ONE = '2026-10-01'

/** Simulated "Day N" label (demo mode), counting 1 Oct 2026 IST as day 1. */
export function demoDay(iso: string): number {
  const day = istDay.format(new Date(iso))
  const diff = Date.parse(day) - Date.parse(DEMO_DAY_ONE)
  return Math.round(diff / 86_400_000) + 1
}

/** Remaining time "3h 12m" until `untilIso` from `nowMs`, or null if past. */
export function timeLeft(untilIso: string, nowMs: number): string | null {
  const ms = Date.parse(untilIso) - nowMs
  if (ms <= 0) return null
  const minutes = Math.floor(ms / 60_000)
  const hours = Math.floor(minutes / 60)
  return hours > 0 ? `${hours}h ${minutes % 60}m` : `${minutes}m`
}

/** Seconds since a timestamp, for "Updated 2s ago". */
export function secondsSince(epochMs: number, nowMs: number): number {
  return Math.max(0, Math.round((nowMs - epochMs) / 1000))
}
