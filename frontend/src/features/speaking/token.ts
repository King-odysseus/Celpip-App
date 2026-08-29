/** Guest-token header used to authorize a loose speaking session. */
export function tokenHeaders(sessionId: string): Record<string, string> {
  const token = sessionStorage.getItem(`celpip-guest-${sessionId}`)
  return token ? { 'X-Guest-Token': token } : {}
}
