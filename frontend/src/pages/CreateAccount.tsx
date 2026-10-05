import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const EMPTY = {
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  confirm_password: '',
}

export default function CreateAccount() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  function update(field: keyof typeof EMPTY) {
    return (event: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: event.target.value }))
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.')
      return
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setPending(true)
    try {
      await register(form)
      navigate('/products')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="page form-page">
      <h1>Create account</h1>
      <p className="form-lede">
        An account keeps your chat history and lets the assistant greet you by name.
      </p>

      {error && <p className="notice notice-error">{error}</p>}

      <form className="form" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            First name
            <input
              required
              autoComplete="given-name"
              value={form.first_name}
              onChange={update('first_name')}
            />
          </label>
          <label>
            Last name
            <input
              required
              autoComplete="family-name"
              value={form.last_name}
              onChange={update('last_name')}
            />
          </label>
        </div>
        <label>
          Email
          <input
            type="email"
            required
            autoComplete="email"
            placeholder="you@yale.edu"
            value={form.email}
            onChange={update('email')}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={form.password}
            onChange={update('password')}
          />
        </label>
        <label>
          Confirm password
          <input
            type="password"
            required
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={update('confirm_password')}
          />
        </label>
        <button type="submit" className="btn btn-primary" disabled={pending}>
          {pending ? 'Creating…' : 'Create account'}
        </button>
      </form>

      <p className="form-foot">
        Already have one? <Link to="/login">Log in</Link>.
      </p>
    </section>
  )
}
