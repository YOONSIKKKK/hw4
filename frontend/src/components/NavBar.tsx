import { useEffect, useState } from 'react'
import { NavLink, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

type NavItem = { to: string; label: string; end?: boolean }

const baseLinks: NavItem[] = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Shop' },
  { to: '/about', label: 'About' },
]

const guestLinks: NavItem[] = [
  { to: '/login', label: 'Log In' },
  { to: '/create-account', label: 'Join' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [stuck, setStuck] = useState(false)

  useEffect(() => {
    const onScroll = () => setStuck(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  const links = user ? baseLinks : [...baseLinks, ...guestLinks]

  return (
    <header className={stuck ? 'nav is-stuck' : 'nav'}>
      <Link to="/" className="nav-brand">
        <span className="nav-brand-mark">Y</span>
        <span>
          <span className="nav-brand-name">Campus Customs</span>
          <small>Yale Bulldog Blue</small>
        </span>
      </Link>
      <nav className="nav-links">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
          >
            {link.label}
          </NavLink>
        ))}
        {user && (
          <>
            <span className="nav-user">{user.first_name ?? user.name}</span>
            <button className="nav-link nav-logout" onClick={handleLogout}>
              Log Out
            </button>
          </>
        )}
      </nav>
    </header>
  )
}
