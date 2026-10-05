import { useEffect, useMemo, useState } from 'react'
import { fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import { useReveal } from '../useReveal'
import type { Product } from '../types'

/** garment_type is free text with 22 spellings, so group it into real categories. */
const CATEGORIES: { label: string; match: (type: string) => boolean }[] = [
  { label: 'All', match: () => true },
  { label: 'Hoodies', match: (t) => t.includes('hood') },
  { label: 'Crewnecks', match: (t) => t.includes('crew') && !t.includes('t-shirt') },
  { label: 'T-shirts', match: (t) => t.includes('t-shirt') || t.includes('tshirt') },
  { label: 'Quarter-zips', match: (t) => t.includes('zip') && !t.includes('full-zip hood') },
  { label: 'Jackets & fleece', match: (t) => t.includes('jacket') || t.includes('fleece') },
]

type Sort = 'featured' | 'price_asc' | 'price_desc'

const SORTS: { value: Sort; label: string }[] = [
  { value: 'featured', label: 'Featured' },
  { value: 'price_asc', label: 'Price: low to high' },
  { value: 'price_desc', label: 'Price: high to low' },
]

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')
  const [sort, setSort] = useState<Sort>('featured')
  const [inStockOnly, setInStockOnly] = useState(false)

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const matcher = CATEGORIES.find((c) => c.label === category) ?? CATEGORIES[0]
    const filtered = products.filter((product) => {
      if (inStockOnly && product.total_stock === 0) return false
      if (!matcher.match(product.garment_type.toLowerCase())) return false
      if (!needle) return true
      return (
        product.name.toLowerCase().includes(needle) ||
        product.description.toLowerCase().includes(needle) ||
        product.garment_type.toLowerCase().includes(needle) ||
        product.colors.some((c) => c.toLowerCase().includes(needle)) ||
        product.search_tags.some((t) => t.toLowerCase().includes(needle))
      )
    })
    if (sort === 'price_asc') return [...filtered].sort((a, b) => a.price - b.price)
    if (sort === 'price_desc') return [...filtered].sort((a, b) => b.price - a.price)
    return filtered
  }, [products, query, category, sort, inStockOnly])

  const root = useReveal<HTMLDivElement>([visible.length])
  const filtered = visible.length !== products.length

  function reset() {
    setQuery('')
    setCategory('All')
    setSort('featured')
    setInStockOnly(false)
  }

  return (
    <div className="page" ref={root}>
      <header className="page-head">
        <div>
          <p className="eyebrow">The collection</p>
          <h1>Everything we make</h1>
        </div>
        <p className="section-note">
          {loading
            ? 'Loading the catalogue…'
            : `Showing ${visible.length} of ${products.length} pieces.`}
        </p>
      </header>

      {error && (
        <p className="notice notice-error">
          Couldn't load products ({error}). Is the API running on port 8000?
        </p>
      )}

      <div className="toolbar">
        <input
          className="toolbar-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search — bulldog, Saybrook, navy, mom…"
          aria-label="Search products"
        />
        <div className="chips">
          {CATEGORIES.map((item) => (
            <button
              key={item.label}
              className={item.label === category ? 'chip chip-on' : 'chip'}
              onClick={() => setCategory(item.label)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="toolbar-end">
          <button
            className={inStockOnly ? 'chip chip-on' : 'chip'}
            onClick={() => setInStockOnly((v) => !v)}
          >
            In stock only
          </button>
          <select
            className="toolbar-sort"
            value={sort}
            onChange={(event) => setSort(event.target.value as Sort)}
            aria-label="Sort products"
          >
            {SORTS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!loading && visible.length === 0 ? (
        <div className="empty">
          <h2>Nothing matches that</h2>
          <p>
            No pieces fit “{query || category}”. Try a broader word, or ask the shop assistant in
            the corner — it searches the catalogue differently.
          </p>
          <button className="btn" onClick={reset}>
            Clear filters
          </button>
        </div>
      ) : (
        <div className="grid">
          {visible.map((product) => (
            <ProductCard key={product.product_id} product={product} />
          ))}
        </div>
      )}

      {filtered && visible.length > 0 && (
        <button className="btn clear-all" onClick={reset}>
          Clear filters
        </button>
      )}
    </div>
  )
}
