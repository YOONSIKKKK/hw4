import type { Product } from './types'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<Product[]>('/api/products')

export const fetchProduct = (productId: string) =>
  getJson<Product>(`/api/products/${productId}`)
