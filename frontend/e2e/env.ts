// Shared E2E settings, read from the repo-root .env (never committed).
import { readFileSync } from 'node:fs'

function dotenv(): Record<string, string> {
  try {
    const text = readFileSync(new URL('../../.env', import.meta.url), 'utf8')
    return Object.fromEntries(
      text
        .split('\n')
        .filter((l) => /^[A-Z_]+=/.test(l))
        .map((l) => {
          const [key, ...rest] = l.split('=')
          return [
            key,
            rest
              .join('=')
              .replace(/\s+#.*$/, '')
              .trim(),
          ]
        }),
    )
  } catch {
    return {}
  }
}

const env = dotenv()
export const API_PORT = 8020
export const WEB_PORT = 5180
export const TEST_DATABASE_URL = process.env.TEST_DATABASE_URL ?? env.TEST_DATABASE_URL ?? ''
export const SEED_PASSWORD = process.env.THUNAI_SEED_PASSWORD ?? env.THUNAI_SEED_PASSWORD ?? ''
