import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  api,
  ensureCsrfToken,
  setAccessToken,
  setRefreshHandler,
} from '../../lib/api'
import type { AuthUser, LearnerProfile, ProfileUpdate } from './types'

type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

type RegisterResult = { recoveryCode: string }

type AuthContextValue = {
  status: AuthStatus
  user: AuthUser | null
  profile: LearnerProfile | null
  register: (identifier: string, password: string) => Promise<RegisterResult>
  login: (identifier: string, password: string) => Promise<void>
  logout: () => Promise<void>
  /** Drop the in-memory session without calling the API (used after deletion). */
  clearSession: () => void
  updateProfile: (changes: ProfileUpdate) => Promise<LearnerProfile>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

type LoginResponse = { access: string; user: AuthUser }
type RegisterResponse = { access: string; user: AuthUser; recovery_code: string }
type RefreshResponse = { access: string; user_id?: number }

const AUTH_ACCOUNT_EVENT_KEY = 'celpip-auth-account-event'

function broadcastAccountChange(userId: number | null): void {
  try {
    localStorage.setItem(AUTH_ACCOUNT_EVENT_KEY, JSON.stringify({
      userId,
      nonce: `${Date.now()}-${Math.random()}`,
    }))
  } catch {
    // Cross-tab signalling is a convenience; auth still works without storage.
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<AuthUser | null>(null)
  const [profile, setProfile] = useState<LearnerProfile | null>(null)
  const activeUserIdRef = useRef<number | null>(null)
  const refreshInFlightRef = useRef<Promise<boolean> | null>(null)

  // Refresh must be callable from the API client's 401 hook without depending
  // on React state, so it lives in a ref-stable callback.
  const refresh = useCallback(async (): Promise<boolean> => {
    if (refreshInFlightRef.current) return refreshInFlightRef.current

    const pending = (async () => {
      try {
        const { access, user_id: refreshedUserId } =
          await api.post<RefreshResponse>('/auth/refresh/')
        const expectedUserId = activeUserIdRef.current
        if (
          expectedUserId !== null
          && refreshedUserId !== undefined
          && refreshedUserId !== expectedUserId
        ) {
          // Another tab signed into a different account and replaced the shared
          // HttpOnly cookie. Never adopt that account's token in this tab.
          setAccessToken(null)
          activeUserIdRef.current = null
          setUser(null)
          setProfile(null)
          setStatus('anonymous')
          return false
        }
        setAccessToken(access)
        return true
      } catch {
        setAccessToken(null)
        activeUserIdRef.current = null
        setUser(null)
        setProfile(null)
        setStatus('anonymous')
        return false
      }
    })()
    refreshInFlightRef.current = pending
    try {
      return await pending
    } finally {
      refreshInFlightRef.current = null
    }
  }, [])

  const loadProfile = useCallback(async () => {
    const nextProfile = await api.get<LearnerProfile>('/me/profile/')
    setProfile(nextProfile)
  }, [])

  const establishSession = useCallback(async () => {
    const [me] = await Promise.all([api.get<AuthUser>('/me/'), loadProfile()])
    activeUserIdRef.current = me.id
    setUser(me)
    setStatus('authenticated')
    broadcastAccountChange(me.id)
  }, [loadProfile])

  // Run the refresh-on-load bootstrap exactly once.
  const bootstrapped = useRef(false)
  useEffect(() => {
    if (bootstrapped.current) return
    bootstrapped.current = true

    setRefreshHandler(refresh)
    let active = true
    ;(async () => {
      await ensureCsrfToken()
      const refreshed = await refresh()
      if (!active) return
      if (!refreshed) {
        setStatus('anonymous')
        return
      }
      try {
        await establishSession()
      } catch {
        if (active) setStatus('anonymous')
      }
    })()

    return () => {
      active = false
      setRefreshHandler(null)
    }
  }, [refresh, establishSession])

  const register = useCallback(
    async (identifier: string, password: string): Promise<RegisterResult> => {
      const data = await api.post<RegisterResponse>('/auth/register/', {
        identifier,
        password,
      })
      setAccessToken(data.access)
      activeUserIdRef.current = data.user.id
      setUser(data.user)
      await loadProfile()
      setStatus('authenticated')
      broadcastAccountChange(data.user.id)
      return { recoveryCode: data.recovery_code }
    },
    [loadProfile],
  )

  const login = useCallback(
    async (identifier: string, password: string): Promise<void> => {
      const data = await api.post<LoginResponse>('/auth/login/', {
        identifier,
        password,
      })
      setAccessToken(data.access)
      activeUserIdRef.current = data.user.id
      setUser(data.user)
      await loadProfile()
      setStatus('authenticated')
      broadcastAccountChange(data.user.id)
    },
    [loadProfile],
  )

  const logout = useCallback(async (): Promise<void> => {
    try {
      await api.post('/auth/logout/')
    } finally {
      setAccessToken(null)
      activeUserIdRef.current = null
      setUser(null)
      setProfile(null)
      setStatus('anonymous')
      broadcastAccountChange(null)
    }
  }, [])

  const clearSession = useCallback((): void => {
    setAccessToken(null)
    activeUserIdRef.current = null
    setUser(null)
    setProfile(null)
    setStatus('anonymous')
    broadcastAccountChange(null)
  }, [])

  useEffect(() => {
    function handleAccountChange(event: StorageEvent) {
      if (event.key !== AUTH_ACCOUNT_EVENT_KEY || !event.newValue) return
      try {
        const changed = JSON.parse(event.newValue) as { userId?: number | null }
        const currentUserId = activeUserIdRef.current
        if (currentUserId !== null && changed.userId !== currentUserId) {
          setAccessToken(null)
          activeUserIdRef.current = null
          setUser(null)
          setProfile(null)
          setStatus('anonymous')
        }
      } catch {
        // Ignore malformed or unrelated storage values.
      }
    }

    window.addEventListener('storage', handleAccountChange)
    return () => window.removeEventListener('storage', handleAccountChange)
  }, [])

  const updateProfile = useCallback(
    async (changes: ProfileUpdate): Promise<LearnerProfile> => {
      const updated = await api.patch<LearnerProfile>('/me/profile/', changes)
      setProfile(updated)
      return updated
    },
    [],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      profile,
      register,
      login,
      logout,
      clearSession,
      updateProfile,
      refreshProfile: loadProfile,
    }),
    [status, user, profile, register, login, logout, clearSession, updateProfile, loadProfile],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
