import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import { useReveal } from '../useReveal'
import type { Product } from '../types'

const TICKER = [
  'Officially licensed Yale apparel',
  '57 Broadway, New Haven',
  'Sizes XS–XXL',
  'Residential colleges',
  'Game day',
  'Live stock on every page',
]

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])
  const root = useReveal<HTMLDivElement>([featured.length])

  useEffect(() => {
    fetchProducts()
      .then((all) => setFeatured(all.filter((p) => p.total_stock > 0).slice(0, 10)))
      .catch(() => setFeatured([]))
  }, [])

  return (
    <div ref={root}>
      <section className="hero">
        <p className="eyebrow reveal">Est. New Haven — Officially licensed</p>
        <h1 className="reveal">
          Big pride,
          <em>stitched in blue.</em>
        </h1>
        <div className="hero-meta">
          <p className="hero-lede reveal">
            The hoodie you live in through reading week. The crewneck with your college across the
            chest. The quarter-zip your dad still wears to every home game.
          </p>
          <div className="hero-actions reveal">
            <Link to="/products" className="btn btn-primary">
              Shop the collection <span className="arrow">→</span>
            </Link>
            <Link to="/about" className="btn">
              Our story
            </Link>
          </div>
        </div>
      </section>

      <div className="ticker">
        <div className="ticker-track">
          {[0, 1].map((copy) => (
            <span key={copy}>
              {TICKER.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </span>
          ))}
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <span className="section-num">01</span>
          <h2>In stock now</h2>
          <p className="section-note">
            Pulled live from the shop floor — if it's here, we have it in at least one size.
          </p>
        </div>
        <div className="rail">
          {featured.map((product) => (
            <ProductCard key={product.product_id} product={product} />
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <span className="section-num">02</span>
          <h2>Three reasons people walk in</h2>
        </div>
        <div className="tiles">
          <article className="tile reveal">
            <span className="micro">Game day</span>
            <div>
              <h3>The Game comes once a year.</h3>
              <p>Show up in something that makes clear which side of the field you're on.</p>
            </div>
          </article>
          <article className="tile reveal">
            <span className="micro">Residential colleges</span>
            <div>
              <h3>Branford to Benjamin Franklin.</h3>
              <p>Crewnecks and quarter-zips printed for the people who actually live there.</p>
            </div>
          </article>
          <article className="tile reveal">
            <span className="micro">Family</span>
            <div>
              <h3>Yale Mom. Yale Dad. Yale Grandma.</h3>
              <p>Someone back home has been waiting four years for this sweatshirt.</p>
            </div>
          </article>
        </div>
      </section>

      <section className="strip">
        <div className="reveal">
          <strong>57 Broadway</strong>
          <span>New Haven, CT — a few minutes from Old Campus</span>
        </div>
        <div className="reveal">
          <strong>XS – XXL</strong>
          <span>Live stock counts on every product page</span>
        </div>
        <div className="reveal">
          <strong>Ask the shop</strong>
          <span>Our assistant knows the catalogue — bottom right</span>
        </div>
      </section>
    </div>
  )
}
