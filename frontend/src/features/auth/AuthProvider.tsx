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
type RefreshResponse = { access: string }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<AuthUser | null>(null)
  const [profile, setProfile] = useState<LearnerProfile | null>(null)

  // Refresh must be callable from the API client's 401 hook without depending
  // on React state, so it lives in a ref-stable callback.
  const refresh = useCallback(async (): Promise<boolean> => {
    try {
      const { access } = await api.post<RefreshResponse>('/auth/refresh/')
      setAccessToken(access)
      return true
    } catch {
      setAccessToken(null)
      return false
    }
  }, [])

  const loadProfile = useCallback(async () => {
    const nextProfile = await api.get<LearnerProfile>('/me/profile/')
    setProfile(nextProfile)
  }, [])

  const establishSession = useCallback(async () => {
    const [me] = await Promise.all([api.get<AuthUser>('/me/'), loadProfile()])
    setUser(me)
    setStatus('authenticated')
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
      setUser(data.user)
      await loadProfile()
      setStatus('authenticated')
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
      setUser(data.user)
      await loadProfile()
      setStatus('authenticated')
    },
    [loadProfile],
  )

  const logout = useCallback(async (): Promise<void> => {
    try {
      await api.post('/auth/logout/')
    } finally {
      setAccessToken(null)
      setUser(null)
      setProfile(null)
      setStatus('anonymous')
    }
  }, [])

  const clearSession = useCallback((): void => {
    setAccessToken(null)
    setUser(null)
    setProfile(null)
    setStatus('anonymous')
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
