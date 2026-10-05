# Usability Improvements

Four enhancements — two on the frontend, two on the agent/backend. All four are live in the
running app and listed below with what they do, how to see them, and why they're worth having.

---

## Frontend

### F1. Shop filter bar — search, categories, stock toggle, sort

**What was built.** A sticky toolbar on the Shop page: a free-text search that matches name,
description, garment type, colors *and* the catalogue's search tags; category chips (All,
Hoodies, Crewnecks, T-shirts, Quarter-zips, Jackets & fleece); an "In stock only" toggle; and a
sort control (Featured / price low→high / price high→low). A live "Showing 27 of 102 pieces"
count sits in the header, and when nothing matches, a proper empty state explains why and offers
one click to clear the filters.

The category chips are not a naive `garment_type` match. That column holds 22 different spellings
for roughly eight real categories (`hoodie`, `pullover hoodie`, `hooded sweatshirt`, `hooded
pullover sweatshirt`…), so each chip matches a family of spellings — "Hoodies" returns all 27,
not the 18 that happen to use one exact string.

**Why it matters.** 102 products in a single unlabelled grid is a wall. A shopper who wants a
grey crewneck under $70 had no way to express that except scrolling. Filtering turns browsing
into finding — and "In stock only" means nobody spends attention on a product they can't buy,
which is the most annoying way to lose a sale.

### F2. Chat starter chips and a panel that stays where you left it

**What was built.** When the conversation is empty, the chat panel offers four tappable starter
questions ("What hoodies do you have?", "Anything under $40?", "Show me Saybrook gear", "What's
your cheapest fleece?") that send on click. The panel's open/closed state is persisted to
`localStorage`, so it survives both navigation to a product page and a full page reload.

**Why it matters.** The hardest part of a chat assistant is the empty box — most people don't
know what it can do, so they never type anything. The chips demonstrate the range (category,
budget, residential college, superlative) in one glance and get the first message sent with a
tap. And since the assistant's whole value is answering questions *while* you look at products,
having it close itself every time you clicked through to an item was actively working against
the feature.

---

## Agent / backend

### B1. Data layer: N+1 query removed, catalogue cached

**What was built.** `GET /api/products` was issuing **103 queries per request** — one for the
catalogue, then one inventory lookup per product. Inventory is now fetched for every product in
a single `IN (…)` query, and the catalogue (static reference data, JSON columns already decoded,
search fields already lowercased) is parsed once and held in memory, keyed on the database file's
mtime and size so a replaced data pack is picked up without a restart.

**Inventory is deliberately *not* cached.** Stock is the one thing that must be true at the
moment it's read, so every availability answer still hits the table.

Measured over 5 runs each:

| Call | Before | After |
|---|---|---|
| `list_products()` | 36.7 ms · 103 queries | **8.0 ms · 2 queries** |
| `search_products("hoodie")` | 31.6 ms · 28 queries | **2.2 ms · 1 query** |
| `get_product()` | 3.4 ms · 2 queries | **1.3 ms · 1 query** |

**Why it matters.** Search is on the agent's critical path — the shopper is watching a typing
indicator while it runs, and a chat turn can make several tool calls. Taking the search from
31.6 ms to 2.2 ms comes straight off the time-to-answer. For the business it's the same product
on cheaper infrastructure: the Shop page got ~4.6× faster and now costs the database two queries
instead of 103.

### B2. Price-aware search — budgets and superlatives answered from the whole catalogue

**What was built.** `search_catalogue` gained `max_price`, `min_price` and
`sort` (`relevance` / `price_asc` / `price_desc`), applied across the **entire** catalogue before
results are trimmed. The prompt has a lookup table mapping shopper phrasings to arguments, and
the tool additionally recovers a price constraint left in the query text ("under $40", "between
40 and 70 bucks", "cheapest", "priciest") as a fallback.

**Why it matters — this fixed a real wrong answer.** Asked "show me anything under $40", the
agent previously replied *"I don't see anything under $40 right now"* while the shop had **25
items at $32**. It had searched the words and compared the handful of rows that came back. That
is a lost sale and a shopper told, confidently, something false about the store. Now the
database does the filtering and the same question returns all eight $32 tees with cards.

Verified against ground truth read directly from the database in the same script: cheapest price
$32, dearest $98, 25 items at or under $40.

| Question | Answer now |
|---|---|
| "im on a budget, whats the most i can get for under $40?" | The $32 tees, with cards |
| "got any sweatshirts between 40 and 70 bucks?" | In-range sweatshirts only, $45–$58 |
| "which single item is the priciest in the whole shop?" | Benjamin Franklin Fleece Jacket, $98 |

---

## Where to see them live

| Enhancement | Where |
|---|---|
| F1 | **Shop** page — type in the search box, tap a category chip, toggle "In stock only", change the sort |
| F2 | Open the assistant (bottom right) — the four starter chips appear; click a product and the panel stays open; reload and it's still open |
| B1 | Shop page loads noticeably faster; benchmark numbers above |
| B2 | Ask the assistant "anything under $40?" or "what's your cheapest fleece?" |
