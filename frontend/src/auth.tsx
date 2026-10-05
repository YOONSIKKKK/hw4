import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { User } from './types'

type AuthValue = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => Promise<void>
}

export type RegisterPayload = {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

const AuthContext = createContext<AuthValue | null>(null)

async function post(path: string, body?: unknown): Promise<Response> {
  return fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: body ? JSON.stringify(body) : undefined,
  })
}

async function failureMessage(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail) && data.detail[0]?.msg) return data.detail[0].msg
  } catch {
    /* body wasn't JSON */
  }
  return fallback
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'same-origin' })
      .then((res) => (res.ok ? res.json() : null))
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const res = await post('/api/auth/login', { email, password })
    if (!res.ok) throw new Error(await failureMessage(res, 'Could not log in.'))
    setUser(await res.json())
  }

  async function register(payload: RegisterPayload) {
    const res = await post('/api/auth/register', payload)
    if (!res.ok) throw new Error(await failureMessage(res, 'Could not create the account.'))
    setUser(await res.json())
  }

  async function logout() {
    await post('/api/auth/logout')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
