import { useEffect, useRef } from 'react'

/**
 * Fades `.reveal` elements in as they scroll into view.
 *
 * Fails safe: elements are visible by default and only *armed* (hidden) if
 * they start below the fold, so a broken timer, a reduced-motion preference
 * or no JS at all can never leave content invisible.
 */
export function useReveal<T extends HTMLElement>(deps: unknown[] = []) {
  const ref = useRef<T>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const limit = () => window.innerHeight - 40
    const inView = (el: HTMLElement) => {
      const rect = el.getBoundingClientRect()
      return rect.top < limit() && rect.bottom > 0
    }

    // `.shown` marks an element this hook has already released, so a re-run
    // (a list arriving after mount) adopts anything still armed instead of
    // orphaning it, and never re-hides something the shopper has seen.
    const candidates = Array.from(node.querySelectorAll<HTMLElement>('.reveal:not(.shown)'))
    let pending = candidates.filter((el) => el.classList.contains('armed') || !inView(el))
    pending.forEach((el) => el.classList.add('armed'))
    candidates
      .filter((el) => !pending.includes(el))
      .forEach((el) => el.classList.add('shown'))
    if (!pending.length) return

    let timer: number | undefined
    const release = () => {
      pending = pending.filter((el) => {
        if (!inView(el)) return true
        el.classList.remove('armed')
        el.classList.add('shown')
        return false
      })
      if (!pending.length) stop()
    }
    const schedule = () => {
      if (timer === undefined) timer = window.setTimeout(() => {
        timer = undefined
        release()
      }, 60)
    }
    // Polled as well as event-driven: some embedded webviews never deliver
    // scroll events, and a card that stays hidden is worse than a lost effect.
    const poll = window.setInterval(release, 250)
    const stop = () => {
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
      clearInterval(poll)
      if (timer !== undefined) clearTimeout(timer)
    }

    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return stop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return ref
}
