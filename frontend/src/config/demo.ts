// Demo mode shows the clock bar and SIMULATED chips (DESIGN §1.5). Not a secret.
export const DEMO_MODE = (import.meta.env.VITE_DEMO_MODE ?? 'true') === 'true'

// Optional demo-account password for one-click sign-in on the login page. It is bundled into
// public JS, so set it only for local or LAN demos with the synthetic seed users, never hosted.
export const DEMO_AUTOFILL_PASSWORD = DEMO_MODE
  ? (import.meta.env.VITE_DEMO_AUTOFILL_PASSWORD ?? '')
  : ''
