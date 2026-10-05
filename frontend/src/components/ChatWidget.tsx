import { useEffect, useRef, useState } from 'react'
import { Link, matchPath, useLocation } from 'react-router-dom'
import Markdown from 'react-markdown'
import { useAuth } from '../auth'
import type { ChatTurn, Product } from '../types'

const GREETING: ChatTurn = {
  role: 'assistant',
  content: "Hi! I'm the Campus Customs shop assistant. Ask me about Yale gear — sizes, colors, prices.",
  products: [],
}

type PageContext = { path: string; product_id: string | null }

async function sendToAgent(
  message: string,
  history: ChatTurn[],
  page: PageContext,
): Promise<{ message: string; products: Product[] }> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify({
      message,
      history: history.map(({ role, content }) => ({ role, content })),
      page,
    }),
  })
  if (!res.ok) throw new Error('unavailable')
  return res.json()
}

function shorten(text: string, limit = 90) {
  if (text.length <= limit) return text
  return `${text.slice(0, text.lastIndexOf(' ', limit))}…`
}

function ProductResults({ products }: { products: Product[] }) {
  return (
    <div className="chat-products">
      <p className="chat-products-head">
        {products.length} {products.length === 1 ? 'match' : 'matches'} from the catalogue
      </p>
      {products.map((product) => (
        <Link
          key={product.product_id}
          to={`/products/${product.product_id}`}
          className="chat-product"
        >
          <img src={product.image_url} alt={product.name} loading="lazy" />
          <span className="chat-product-text">
            <span className="chat-product-name">{product.name}</span>
            <span className="chat-product-price">${product.price.toFixed(2)}</span>
            <span className="chat-product-desc">{shorten(product.description)}</span>
          </span>
        </Link>
      ))}
    </div>
  )
}

const STARTERS = [
  'What hoodies do you have?',
  'Anything under $40?',
  'Show me Saybrook gear',
  "What's your cheapest fleece?",
]

const OPEN_KEY = 'cc.chat.open'

export default function ChatWidget() {
  const { user } = useAuth()
  const location = useLocation()
  // Survives navigation and reloads: a shopper who opened the assistant
  // shouldn't have to find it again after clicking through to a product.
  const [open, setOpen] = useState(() => localStorage.getItem(OPEN_KEY) === '1')
  const [messages, setMessages] = useState<ChatTurn[]>([GREETING])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  // A signed-in shopper's conversation is stored server-side; a guest starts fresh.
  useEffect(() => {
    if (!user) {
      setMessages([GREETING])
      return
    }
    fetch('/api/chat/history', { credentials: 'same-origin' })
      .then((res) => (res.ok ? res.json() : []))
      .then((turns: ChatTurn[]) => setMessages(turns.length ? turns : [GREETING]))
      .catch(() => setMessages([GREETING]))
  }, [user])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  useEffect(() => {
    localStorage.setItem(OPEN_KEY, open ? '1' : '0')
  }, [open])

  async function send(text: string) {
    if (!text || pending) return
    const history = messages
    setMessages([...history, { role: 'user', content: text, products: [] }])
    setDraft('')
    setPending(true)
    const onProduct = matchPath('/products/:productId', location.pathname)
    const page: PageContext = {
      path: location.pathname,
      product_id: onProduct?.params.productId ?? null,
    }
    try {
      const reply = await sendToAgent(text, history, page)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: reply.message, products: reply.products },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: "Sorry — I couldn't reach the shop just now. Try again in a moment.",
          products: [],
        },
      ])
    } finally {
      setPending(false)
    }
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    send(draft.trim())
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setOpen(true)}>
        <i />
        Ask the shop
      </button>
    )
  }

  return (
    <section className="chat-panel">
      <header className="chat-header">
        <span>
          <strong>Shop Assistant</strong>
          <small>Campus Customs</small>
        </span>
        <button onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </header>
      <div className="chat-log">
        {messages.map((message, index) => (
          <div key={index} className={`chat-turn chat-turn-${message.role}`}>
            <div className={`chat-msg chat-msg-${message.role}`}>
              <Markdown>{message.content}</Markdown>
            </div>
            {message.products && message.products.length > 0 && (
              <ProductResults products={message.products} />
            )}
          </div>
        ))}
        {pending && (
          <div className="chat-msg chat-msg-assistant chat-typing">
            <i />
            <i />
            <i />
          </div>
        )}
        {messages.length === 1 && !pending && (
          <div className="chat-starters">
            {STARTERS.map((starter) => (
              <button key={starter} className="chip" onClick={() => send(starter)}>
                {starter}
              </button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="What hoodies do you have?"
        />
        <button type="submit" disabled={pending} aria-label="Send">
          →
        </button>
      </form>
    </section>
  )
}
