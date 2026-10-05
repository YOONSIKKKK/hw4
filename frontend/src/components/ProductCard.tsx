import { Link } from 'react-router-dom'
import type { Product } from '../types'

function shorten(text: string, limit = 96) {
  if (text.length <= limit) return text
  return `${text.slice(0, text.lastIndexOf(' ', limit))}…`
}

export default function ProductCard({ product }: { product: Product }) {
  return (
    <Link to={`/products/${product.product_id}`} className="card reveal">
      <div className="card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className="card-type">{product.garment_type}</span>
        {product.total_stock === 0 && <span className="badge-out">Sold out</span>}
      </div>
      <div className="card-body">
        <div className="card-row">
          <h3>{product.name}</h3>
          <span className="card-price">${product.price.toFixed(2)}</span>
        </div>
        <p className="card-desc">{shorten(product.description)}</p>
      </div>
    </Link>
  )
}
