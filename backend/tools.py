"""Tools the Campus Customs agent can call.

Every tool is read-only, reads live from campus_customs.db, returns a typed model
from models.py, and records what it returned on the shared dependency object — so
the product panel can only ever show items the catalogue actually produced.
"""

import re
import time
from dataclasses import dataclass, field

from pydantic_ai import RunContext

import audit
import db
from models import LookupMiss, Product, ProductSummary, SizeVerdict, StockReport

MAX_RESULTS = 12


@dataclass
class Customer:
    """The signed-in shopper, as the agent is allowed to know them."""

    id: int
    name: str
    email: str
    first_name: str | None


@dataclass
class ShopDeps:
    """Per-request state handed to every tool and to the dynamic instructions.

    This is the whole of what the agent knows about who it's talking to and
    where they are — nothing is read from globals or from the model's memory.
    """

    customer: Customer | None = None
    page_path: str = "/"
    page_product: Product | None = None
    shown: list[Product] = field(default_factory=list)
    run_id: str = "-"
    tool_calls: int = 0

    def record(self, products: list[Product]) -> None:
        seen = {p.product_id for p in self.shown}
        self.shown.extend(p for p in products if p.product_id not in seen)


_MAX_PRICE_RE = re.compile(
    r"(?:under|below|less than|cheaper than|up to|no more than|within|max(?:imum)?(?: of)?)"
    r"\s*\$?\s*(\d+(?:\.\d{1,2})?)",
    re.I,
)
_MAX_PRICE_TRAILING_RE = re.compile(
    r"\$?\s*(\d+(?:\.\d{1,2})?)\s*(?:dollars?|bucks?)?\s*or\s*(?:less|under|below|cheaper)", re.I
)
_MIN_PRICE_RE = re.compile(
    r"(?:over|above|more than|at least|starting (?:at|from)|min(?:imum)?(?: of)?)"
    r"\s*\$?\s*(\d+(?:\.\d{1,2})?)",
    re.I,
)
_BETWEEN_RE = re.compile(
    r"between\s*\$?\s*(\d+(?:\.\d{1,2})?)\s*(?:and|to|-|–)\s*\$?\s*(\d+(?:\.\d{1,2})?)", re.I
)
_CHEAPEST_RE = re.compile(r"\b(cheapest|least expensive|most affordable|lowest pric\w*)\b", re.I)
_DEAREST_RE = re.compile(r"\b(most expensive|priciest|highest pric\w*|dearest)\b", re.I)
_PRICE_NOISE_RE = re.compile(r"\$\s*\d+(?:\.\d{1,2})?|\b\d+(?:\.\d{1,2})?\s*(?:dollars?|bucks?)\b", re.I)


def _infer_price_intent(
    query: str, max_price: float | None, min_price: float | None, sort: str
) -> tuple[str, float | None, float | None, str]:
    """Recover a price constraint the model left in the query text.

    The price arguments are the supported path, but a budget stated only in
    prose ("anything under $40") would otherwise be matched as search terms and
    come back empty — which reads to the shopper as "we have nothing that cheap"
    when in fact we have 25 such items. Parsing it here makes the guarantee hold
    whether or not the arguments were filled in.
    """
    cleaned = query

    between = _BETWEEN_RE.search(query)
    if between:
        low, high = sorted((float(between.group(1)), float(between.group(2))))
        min_price = low if min_price is None else min_price
        max_price = high if max_price is None else max_price
        cleaned = cleaned.replace(between.group(0), " ")

    if max_price is None:
        match = _MAX_PRICE_RE.search(query) or _MAX_PRICE_TRAILING_RE.search(query)
        if match:
            max_price = float(match.group(1))
            cleaned = cleaned.replace(match.group(0), " ")
    if min_price is None:
        match = _MIN_PRICE_RE.search(query)
        if match:
            min_price = float(match.group(1))
            cleaned = cleaned.replace(match.group(0), " ")
    if sort == "relevance":
        if _CHEAPEST_RE.search(query):
            sort = "price_asc"
        elif _DEAREST_RE.search(query):
            sort = "price_desc"

    cleaned = _CHEAPEST_RE.sub(" ", cleaned)
    cleaned = _DEAREST_RE.sub(" ", cleaned)
    cleaned = _PRICE_NOISE_RE.sub(" ", cleaned)
    return " ".join(cleaned.split()), max_price, min_price, sort


def _summarize(product: Product) -> ProductSummary:
    return ProductSummary(
        product_id=product.product_id,
        name=product.name,
        garment_type=product.garment_type,
        price=product.price,
        colors=product.colors,
        description=product.description,
        sizes_in_stock=[i.size for i in product.inventory if i.quantity > 0],
        sizes_sold_out=[i.size for i in product.inventory if i.quantity == 0],
        total_stock=product.total_stock,
    )


async def search_catalogue(
    ctx: RunContext[ShopDeps],
    query: str,
    limit: int = 8,
    max_price: float | None = None,
    min_price: float | None = None,
    sort: str = "relevance",
) -> list[ProductSummary]:
    """Search the Campus Customs catalogue.

    Use this for anything the shopper describes: a garment type ("hoodie", "fleece"), a sport,
    a residential college, a graduate school, a family member ("mom", "dad"), a color, a graphic
    ("bulldog", "Handsome Dan"), or a phrase from how they asked. Matches names, categories,
    colors, tags and descriptions, so partial and fuzzy wording is fine.

    Each result carries the catalogue's own description and price plus which sizes are in stock
    and which are sold out. An empty list means the store genuinely has nothing matching — say
    so rather than inventing something.

    **Use the price arguments instead of eyeballing the results.** For a budget ("under $50")
    pass `max_price`; for "cheapest"/"most affordable" pass `sort="price_asc"`; for
    "nicest"/"most expensive" pass `sort="price_desc"`. The whole catalogue is filtered and
    ordered before the list is cut to `limit`, so the top result really is the cheapest one in
    the store — whereas sorting the handful of rows you happen to get back is not reliable.

    Args:
        query: What the shopper is looking for, in their words. May be empty if they only
            gave a budget ("anything under $40").
        limit: How many products to return (1-12).
        max_price: Only products at or below this price.
        min_price: Only products at or above this price.
        sort: "relevance" (default), "price_asc" for cheapest first, "price_desc" for dearest.
    """
    started = time.perf_counter()
    if sort not in {"relevance", "price_asc", "price_desc"}:
        sort = "relevance"
    query, max_price, min_price, sort = _infer_price_intent(query, max_price, min_price, sort)

    products = db.search_products(
        query,
        limit=max(1, min(limit, MAX_RESULTS)),
        max_price=max_price,
        min_price=min_price,
        sort=sort,
    )
    ctx.deps.record(products)
    ctx.deps.tool_calls += 1
    audit.tool_call(
        ctx.deps.run_id,
        "search_catalogue",
        {"query": query, "limit": limit, "max_price": max_price,
         "min_price": min_price, "sort": sort},
        {"matches": len(products), "names": [p.name for p in products]},
        (time.perf_counter() - started) * 1000,
    )
    return [_summarize(p) for p in products]


async def get_product_details(
    ctx: RunContext[ShopDeps], product_id: str
) -> ProductSummary | LookupMiss:
    """Look up one product's full details by its id, as returned by search_catalogue.

    Use this when the shopper asks about a specific item already under discussion — what it
    looks like, what it's made of, what it costs, or which colors it comes in. The description
    and price returned here are the catalogue's own; report them as given and do not round,
    estimate or embellish.
    """
    started = time.perf_counter()
    product = db.get_product(product_id)
    ctx.deps.tool_calls += 1
    if product is None:
        audit.tool_call(
            ctx.deps.run_id, "get_product_details", {"product_id": product_id},
            {"found": False}, (time.perf_counter() - started) * 1000,
        )
        return LookupMiss()
    ctx.deps.record([product])
    audit.tool_call(
        ctx.deps.run_id,
        "get_product_details",
        {"product_id": product_id},
        {"found": True, "name": product.name, "price": product.price},
        (time.perf_counter() - started) * 1000,
    )
    return _summarize(product)


async def check_size_availability(
    ctx: RunContext[ShopDeps],
    product_id: str,
    size: str | None = None,
) -> StockReport | LookupMiss:
    """Get live stock counts for one product, overall or for a single size.

    Use this whenever the shopper asks about sizes or whether something is available. Every
    product carries all six sizes (XS, S, M, L, XL, XXL); a size with quantity 0 is out of
    stock and cannot be ordered or reserved — tell the shopper plainly that it's unavailable
    rather than hedging. These counts are live; never state a quantity you did not get here.

    Args:
        product_id: The product's id from search_catalogue.
        size: Optional single size to check (XS, S, M, L, XL, XXL). Omit for all sizes.
    """
    started = time.perf_counter()
    product = db.get_product(product_id)
    ctx.deps.tool_calls += 1
    if product is None:
        audit.tool_call(
            ctx.deps.run_id, "check_size_availability",
            {"product_id": product_id, "size": size},
            {"found": False}, (time.perf_counter() - started) * 1000,
        )
        return LookupMiss()
    ctx.deps.record([product])

    quantities = {item.size: item.quantity for item in product.inventory}
    report = StockReport(
        product_id=product.product_id,
        name=product.name,
        price=product.price,
        quantity_by_size=quantities,
        sizes_in_stock=[s for s, q in quantities.items() if q > 0],
        sizes_sold_out=[s for s, q in quantities.items() if q == 0],
        sold_out_entirely=product.total_stock == 0,
        total_stock=product.total_stock,
    )

    if size is not None:
        requested = size.strip().upper()
        if requested not in quantities:
            report.requested_size = SizeVerdict(
                size=requested,
                available=False,
                note=f"{product.name} is not made in that size. It comes in "
                f"{', '.join(quantities)}.",
            )
        else:
            quantity = quantities[requested]
            report.requested_size = SizeVerdict(
                size=requested,
                quantity=quantity,
                available=quantity > 0,
                note=(
                    f"{quantity} left in {requested}."
                    if quantity > 0
                    else f"{requested} is out of stock — none available."
                ),
            )

    audit.tool_call(
        ctx.deps.run_id,
        "check_size_availability",
        {"product_id": product_id, "size": size},
        {
            "name": product.name,
            "in_stock": report.sizes_in_stock,
            "sold_out": report.sizes_sold_out,
            "verdict": report.requested_size.note if report.requested_size else None,
        },
        (time.perf_counter() - started) * 1000,
    )
    return report


TOOLS = [search_catalogue, get_product_details, check_size_availability]
