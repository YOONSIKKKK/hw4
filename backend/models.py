"""Pydantic models for the Campus Customs API."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class InventoryItem(BaseModel):
    size: str
    quantity: int


class Product(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    search_tags: list[str]
    image_file_path: str
    image_url: str
    price: float
    inventory: list[InventoryItem]
    total_stock: int


# ---------- what the agent's tools hand back ----------


class ProductSummary(BaseModel):
    """One catalogue item as the agent sees it.

    Deliberately not the same as `Product`: the model gets the facts a shopper
    could ask about and none of the image plumbing, and sizes arrive pre-sorted
    into in-stock / sold-out so availability is never a judgement call.
    """

    found: Literal[True] = True
    product_id: str
    name: str
    garment_type: str
    price: float
    colors: list[str]
    description: str
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]
    total_stock: int


class SizeVerdict(BaseModel):
    """A yes/no on one specific size, decided from the inventory row."""

    size: str
    quantity: int | None = None
    available: bool
    note: str


class StockReport(BaseModel):
    """Live stock for one product, overall and optionally for one size."""

    found: Literal[True] = True
    product_id: str
    name: str
    price: float
    quantity_by_size: dict[str, int]
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]
    sold_out_entirely: bool
    total_stock: int
    requested_size: SizeVerdict | None = None


class LookupMiss(BaseModel):
    """Returned when an id isn't in the catalogue — never a silent null."""

    found: Literal[False] = False
    note: str = (
        "No product with that id. Call search_catalogue to find the product first, "
        "and never guess a description, price or quantity."
    )


class ChatTurn(BaseModel):
    """One message in a conversation, as the website holds it."""

    role: Literal["user", "assistant"]
    content: str


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message.

    Only the route is taken from the browser — any product named here is
    re-read from the catalogue server-side, so a tampered payload can't put
    false facts in front of the agent.
    """

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(default=None, max_length=120)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)
    page: PageContext | None = None


class ChatReply(BaseModel):
    """The agent's answer plus the product cards the panel should show.

    `products` only ever contains items the agent's tools actually returned from
    the catalogue, so the panel can't display something the model imagined.
    """

    message: str
    products: list[Product] = Field(default_factory=list)


class StoredChatTurn(ChatTurn):
    products: list[Product] = Field(default_factory=list)


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    """Public view of an account — never carries the password hash."""

    id: int
    name: str
    email: str
    first_name: str | None
    last_name: str | None
