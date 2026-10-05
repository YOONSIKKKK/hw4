import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct } from '../api'
import type { Product } from '../types'

const COLOR_SWATCHES: Record<string, string> = {
  navy: '#00356b',
  'navy blue': '#00356b',
  blue: '#1d4ed8',
  white: '#ffffff',
  gray: '#9ca3af',
  grey: '#9ca3af',
  'heather gray': '#b6b8bb',
  'dark heather gray': '#6b7280',
  'heather charcoal': '#4b5563',
  'dark heather charcoal': '#44484f',
  'charcoal gray': '#4b5563',
  charcoal: '#3f4651',
  black: '#111317',
  red: '#b3261e',
  green: '#15803d',
  yellow: '#d6a832',
  gold: '#b08d50',
  pink: '#e7a3b4',
  purple: '#6d28d9',
  maroon: '#7a2231',
  orange: '#d97706',
  cream: '#f1ebdd',
}

function swatchFor(color: string) {
  const key = color.toLowerCase().trim()
  if (COLOR_SWATCHES[key]) return COLOR_SWATCHES[key]
  const base = Object.keys(COLOR_SWATCHES).find((name) => key.includes(name))
  return base ? COLOR_SWATCHES[base] : '#d6d3cc'
}

export default function ProductDetail() {
  const { productId } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!productId) return
    setProduct(null)
    setError(null)
    window.scrollTo({ top: 0 })
    fetchProduct(productId)
      .then(setProduct)
      .catch((err: Error) => setError(err.message))
  }, [productId])

  if (error) {
    return (
      <p className="page notice notice-error">
        Couldn't load this product ({error}). <Link to="/products">Back to all products</Link>
      </p>
    )
  }

  if (!product) return <p className="page notice">Loading…</p>

  const inStock = product.inventory.filter((item) => item.quantity > 0)

  return (
    <article className="detail page">
      <div className="detail-image">
        <img src={product.image_url} alt={product.name} />
      </div>

      <div className="detail-info">
        <Link to="/products" className="back-link">
          ← All products
        </Link>
        <p className="eyebrow">{product.garment_type}</p>
        <h1>{product.name}</h1>
        <p className="detail-price">${product.price.toFixed(2)}</p>
        <p className="detail-desc">{product.description}</p>

        <h2>Colors</h2>
        <ul className="swatches">
          {product.colors.map((color) => (
            <li key={color} className="swatch">
              <i style={{ background: swatchFor(color) }} />
              {color}
            </li>
          ))}
        </ul>

        <h2>Sizes {inStock.length > 0 && <>— {inStock.length} available</>}</h2>
        {inStock.length === 0 ? (
          <p className="notice">Sold out in every size right now.</p>
        ) : (
          <ul className="sizes">
            {product.inventory.map((item) => (
              <li key={item.size} className={item.quantity > 0 ? 'size' : 'size size-out'}>
                <strong>{item.size}</strong>
                <span>{item.quantity > 0 ? `${item.quantity} left` : 'Out'}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="detail-stock">{product.total_stock} units in stock across all sizes.</p>
      </div>
    </article>
  )
}
