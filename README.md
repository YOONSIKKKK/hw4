# Campus Customs — Yale Bulldog Blue

An e-commerce storefront for Campus Customs, the officially licensed Yale apparel shop at
57 Broadway, New Haven — with a shop assistant that answers from the live catalogue.

- **Frontend** — React + Vite + TypeScript
- **Backend** — FastAPI
- **Agent** — PydanticAI, running on Claude Opus 5 through Portkey
- **Data** — SQLite (`campus_customs.db`): 102 products, per-size stock, accounts, chat history

What it does: browse and filter 102 products, open any item for the full description and live
per-size stock, create an account and log in, and chat with an assistant that searches the
catalogue, renders what it finds as clickable product cards, knows which product page you're
looking at, and remembers your conversation between visits.

---

## Setup

### 1. The data pack (local only — not in this repo)

The database and the product images are course-provided and deliberately gitignored. Extract
`data.zip` into the project root so you end up with:

```
data/
├── campus_customs.db
└── products/          # 102 .jpg files referenced by the catalogue
```

### 2. Environment

Copy `.env.example` to `.env` in the project root and fill in your key:

```
PORTKEY_API_KEY=...
SESSION_SECRET=...
```

`.env` is gitignored. The key is read from the environment at startup and is never logged,
printed, or returned by the API.

### 3. Install

From the project root:

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```bash
npm --prefix frontend install
```

(On macOS or Linux the pip line is `.venv/bin/python -m pip install -r requirements.txt`.)

---

## Running it

Two terminals.

**Backend** — from inside `backend/`:

```bash
uvicorn main:app --reload --port 8000
```

**Frontend** — from inside `frontend/`:

```bash
npm run dev
```

Then open **http://localhost:5173**.

Vite proxies `/api` and `/media` to the backend on port 8000, so the browser talks to a single
origin and the session cookie works without any CORS setup.

### Try it

- Browse **Shop** — search "bulldog", filter to Hoodies, toggle "In stock only", sort by price.
- Open any product for the large image, colours, and live per-size stock.
- Open the assistant (bottom right) and ask *"what hoodies do you have?"*, *"anything under $40?"*,
  or — while on a product page — *"do you have this in pink?"*.
- Sign in with the seeded test account to see your conversation restored on your next visit:
  `test@campuscustoms.yale.edu` / `password`.

---

## Layout

```
.
├── AI_prompts.md          # every prompt sent to the coding assistant, with outcomes
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── frontend/              # Vite React TypeScript app
│   └── src/
│       ├── pages/         # Home, Products, ProductDetail, About, Login, CreateAccount
│       ├── components/    # NavBar, ProductCard, ChatWidget
│       ├── auth.tsx       # session state shared across the app
│       └── index.css      # the whole design system
├── backend/
│   ├── main.py            # FastAPI app — the file uvicorn runs
│   ├── agent.py           # PydanticAI agent: model wiring + prompt loading
│   ├── tools.py           # the three tools the agent can call
│   ├── models.py          # Pydantic types shared by the API and the agent
│   ├── db.py              # read access to campus_customs.db
│   ├── auth.py            # password hashing
│   ├── audit.py           # append-only agent-loop log
│   └── prompts/
│       └── prompt.md      # system prompt — voice, grounding rules, safety
├── output/
│   ├── harness.md         # how the system works, end to end
│   ├── design.md          # design decisions and the conversion argument
│   ├── usability.md       # the four usability improvements
│   ├── app_check.html     # screenshot-based check of the live app
│   ├── app_check_images/
│   └── audit_trail.json   # append-only log of agent runs and tool calls
└── data/                  # local only, gitignored
```

## API

| Route | Purpose |
|---|---|
| `GET /api/products` | The whole catalogue, with per-size stock |
| `GET /api/products/{id}` | One product; 404 if unknown |
| `POST /api/chat` | `{message, history, page}` → `{message, products}` |
| `GET /api/chat/history` | Stored conversation for the signed-in shopper |
| `POST /api/auth/register \| login \| logout` | Accounts |
| `GET /api/auth/me` | Current session |
| `GET /media/products/<file>` | Product images, served from the local data pack |

## Notes

- Passwords are stored as PBKDF2-HMAC-SHA256 with 120,000 iterations and a per-user random salt,
  matching the scheme the seeded accounts already use.
- The product cards the assistant shows are built from the rows its tools actually returned, not
  from its text — so it cannot put a card on screen for a product that doesn't exist.
- Stock is read live on every question; only the static catalogue is cached.
- `output/harness.md` is the full technical write-up: data model, tools, safety rules, and specs.
