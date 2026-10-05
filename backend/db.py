"""Read access to campus_customs.db.

JSON-encoded columns are decoded here so the rest of the app only ever sees
real Python lists.
"""

import json
import sqlite3
from pathlib import Path

from models import InventoryItem, Product, User

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
PRODUCT_IMAGE_DIR = DATA_DIR / "products"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def connect_rw() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _size_key(size: str) -> int:
    return SIZE_ORDER.index(size) if size in SIZE_ORDER else len(SIZE_ORDER)


# ---------- catalogue cache ----------
#
# Catalogue rows are static reference data, so they're parsed once (JSON columns
# and all) and held in memory, keyed on the database file's mtime so an updated
# data pack is picked up without a restart. Inventory is deliberately NOT cached:
# stock is the one thing that must be read live on every request.

_catalogue: dict[str, dict] | None = None
_catalogue_stamp: tuple[float, int] | None = None


def _db_stamp() -> tuple[float, int]:
    stat = DB_PATH.stat()
    return (stat.st_mtime, stat.st_size)


def _catalogue_by_id() -> dict[str, dict]:
    global _catalogue, _catalogue_stamp
    stamp = _db_stamp()
    if _catalogue is None or _catalogue_stamp != stamp:
        with connect() as conn:
            rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        _catalogue = {
            row["product_id"]: {
                "product_id": row["product_id"],
                "name": row["name"],
                "garment_type": row["garment_type"],
                "description": row["description"],
                "colors": json.loads(row["colors"]),
                "search_tags": json.loads(row["search_tags"]),
                "image_file_path": row["image_file_path"],
                "image_url": f"/media/{row['image_file_path']}",
                "price": row["price"],
                # lowercased once, for the search scorer
                "_haystacks": {
                    "name": row["name"].lower(),
                    "garment_type": row["garment_type"].lower(),
                    "search_tags": row["search_tags"].lower(),
                    "colors": row["colors"].lower(),
                    "description": row["description"].lower(),
                },
            }
            for row in rows
        }
        _catalogue_stamp = stamp
    return _catalogue


def _inventory_for(product_ids: list[str]) -> dict[str, list[InventoryItem]]:
    """One query for every product asked about, instead of one query each."""
    if not product_ids:
        return {}
    placeholders = ",".join("?" * len(product_ids))
    with connect() as conn:
        rows = conn.execute(
            f"SELECT product_id, size, quantity FROM inventory"
            f" WHERE product_id IN ({placeholders})",
            product_ids,
        ).fetchall()
    grouped: dict[str, list[InventoryItem]] = {pid: [] for pid in product_ids}
    for row in rows:
        grouped[row["product_id"]].append(
            InventoryItem(size=row["size"], quantity=row["quantity"])
        )
    for items in grouped.values():
        items.sort(key=lambda i: _size_key(i.size))
    return grouped


def _build(entry: dict, inventory: list[InventoryItem]) -> Product:
    fields = {k: v for k, v in entry.items() if not k.startswith("_")}
    return Product(
        **fields,
        inventory=inventory,
        total_stock=sum(i.quantity for i in inventory),
    )


def _assemble(entries: list[dict]) -> list[Product]:
    stock = _inventory_for([e["product_id"] for e in entries])
    return [_build(entry, stock.get(entry["product_id"], [])) for entry in entries]


def list_products() -> list[Product]:
    return _assemble(list(_catalogue_by_id().values()))


def get_product(product_id: str) -> Product | None:
    entry = _catalogue_by_id().get(product_id)
    if entry is None:
        return None
    return _build(entry, _inventory_for([product_id])[product_id])


# ---------- search ----------

# garment_type is free text with 22 spellings for roughly eight real categories,
# so a shopper's word is expanded to every variant the catalogue actually uses.
CATEGORY_SYNONYMS = {
    "hoodie": ["hoodie", "hooded"],
    "hoody": ["hoodie", "hooded"],
    "sweatshirt": ["sweatshirt", "crewneck", "hoodie"],
    "crewneck": ["crewneck", "crew-neck"],
    "crew": ["crewneck", "crew-neck"],
    "tee": ["t-shirt", "tshirt"],
    "tees": ["t-shirt", "tshirt"],
    "t-shirt": ["t-shirt", "tshirt"],
    "tshirt": ["t-shirt", "tshirt"],
    "shirt": ["shirt", "t-shirt"],
    "fleece": ["fleece", "quarter-zip"],
    "jacket": ["jacket", "fleece"],
    "zip": ["zip", "quarter-zip"],
    "quarter-zip": ["quarter-zip", "1-4-zip"],
    "pullover": ["pullover"],
    "sweater": ["sweater", "fleece", "crewneck"],
}

FIELD_WEIGHTS = {"name": 5, "garment_type": 4, "search_tags": 3, "colors": 3, "description": 1}


def _terms(query: str) -> list[str]:
    words = [w.strip(".,!?'\"").lower() for w in query.split()]
    expanded: list[str] = []
    for word in words:
        if not word:
            continue
        expanded.extend(CATEGORY_SYNONYMS.get(word, [word]))
    return expanded


def search_products(
    query: str,
    limit: int = 8,
    max_price: float | None = None,
    min_price: float | None = None,
    sort: str = "relevance",
) -> list[Product]:
    """Score every product against the query across name, type, tags, colors and description.

    Price bounds and ordering are applied in the data layer so a budget or a
    "cheapest" question is answered by the database rather than inferred by the
    model from a truncated result list.
    """
    terms = _terms(query) if query.strip() else []

    def collect(active_terms: list[str]) -> list[tuple[int, dict]]:
        found: list[tuple[int, dict]] = []
        for entry in _catalogue_by_id().values():
            if max_price is not None and entry["price"] > max_price:
                continue
            if min_price is not None and entry["price"] < min_price:
                continue
            haystacks = entry["_haystacks"]
            score = sum(
                weight
                for field, weight in FIELD_WEIGHTS.items()
                for term in active_terms
                if term in haystacks[field]
            )
            # With no usable terms a price filter alone is a valid query
            # ("anything under $40"), so everything in range stays in.
            if score or not active_terms:
                found.append((score, entry))
        return found

    scored = collect(terms)

    # "show me anything under $40" leaves filler words behind that match no
    # product, which would wrongly read as "we have nothing that cheap". When a
    # price constraint is doing the real work, drop the words rather than the
    # answer.
    if not scored and terms and (max_price is not None or min_price is not None or sort != "relevance"):
        scored = collect([])

    if sort == "price_asc":
        scored.sort(key=lambda item: (item[1]["price"], -item[0]))
    elif sort == "price_desc":
        scored.sort(key=lambda item: (-item[1]["price"], -item[0]))
    else:
        scored.sort(key=lambda item: (-item[0], item[1]["price"]))

    return _assemble([entry for _, entry in scored[:limit]])


# ---------- chat history ----------


def load_history(user_id: int, limit: int = 40) -> list[sqlite3.Row]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json FROM chat_messages"
            " WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return list(reversed(rows))


def save_message(user_id: int, role: str, content: str, products_json: str | None) -> None:
    conn = connect_rw()
    try:
        with conn:
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json)"
                " VALUES (?, ?, ?, ?)",
                (user_id, role, content, products_json),
            )
    finally:
        conn.close()


# ---------- users ----------


class EmailAlreadyRegistered(Exception):
    pass


def _to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        first_name=row["first_name"],
        last_name=row["last_name"],
    )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_credentials(email: str) -> sqlite3.Row | None:
    """Internal lookup — the only place the stored hash leaves the database."""
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (normalize_email(email),)
        ).fetchone()


def get_user(user_id: int) -> User | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _to_user(row) if row else None


def create_user(first_name: str, last_name: str, email: str, password_hash: str) -> User:
    full_name = f"{first_name} {last_name}".strip()
    conn = connect_rw()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name)"
                " VALUES (?, ?, ?, ?, ?)",
                (full_name, normalize_email(email), password_hash, first_name, last_name),
            )
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _to_user(row)
    except sqlite3.IntegrityError as exc:
        raise EmailAlreadyRegistered() from exc
    finally:
        conn.close()
