/** 2 s polling that backs off 2 → 4 → 8 s … up to 30 s while requests fail (DESIGN §9). */
export function pollEvery(baseMs = 2000) {
  return (query: { state: { fetchFailureCount: number } }): number => {
    const failures = query.state.fetchFailureCount
    return failures ? Math.min(30_000, baseMs * 2 ** failures) : baseMs
  }
}
