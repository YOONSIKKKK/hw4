import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setPending(true)
    try {
      await login(email, password)
      navigate('/products')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="page form-page">
      <h1>Log in</h1>
      <p className="form-lede">Sign in to pick up your conversation with the shop assistant.</p>

      {error && <p className="notice notice-error">{error}</p>}

      <form className="form" onSubmit={handleSubmit}>
        <label>
          Email
          <input
            type="email"
            required
            autoComplete="email"
            placeholder="you@yale.edu"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <button type="submit" className="btn btn-primary" disabled={pending}>
          {pending ? 'Signing in…' : 'Log in'}
        </button>
      </form>

      <p className="form-foot">
        No account yet? <Link to="/create-account">Create one</Link>.
      </p>
    </section>
  )
}
