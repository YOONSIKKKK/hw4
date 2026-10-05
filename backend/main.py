"""Campus Customs API.

Serves the product catalogue and product images for the storefront.
Grows into the agent backend in a later problem.
"""

import json
import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import agent
import auth
import db
from models import (
    ChatReply,
    ChatRequest,
    ChatTurn,
    LoginRequest,
    Product,
    RegisterRequest,
    StoredChatTurn,
    User,
)
from tools import Customer

_PROJECT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_DIR / ".env")
load_dotenv(_PROJECT_DIR.parent / ".env")

log = logging.getLogger("campus_customs")

app = FastAPI(title="Campus Customs API")

# A generated secret is fine for local development; it just invalidates
# existing sessions whenever the server restarts.
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET") or secrets.token_hex(32),
    same_site="lax",
    https_only=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/media/products",
    StaticFiles(directory=db.PRODUCT_IMAGE_DIR),
    name="product-images",
)


@app.get("/api/products", response_model=list[Product])
def get_products() -> list[Product]:
    return db.list_products()


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: str) -> Product:
    product = db.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------- auth ----------


def current_user(request: Request) -> User | None:
    user_id = request.session.get("user_id")
    return db.get_user(user_id) if user_id else None


@app.post("/api/auth/register", response_model=User, status_code=201)
def register(payload: RegisterRequest, request: Request) -> User:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    try:
        user = db.create_user(
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            email=payload.email,
            password_hash=auth.hash_password(payload.password),
        )
    except db.EmailAlreadyRegistered:
        raise HTTPException(status_code=409, detail="That email is already registered.")
    request.session["user_id"] = user.id
    return user


@app.post("/api/auth/login", response_model=User)
def login(payload: LoginRequest, request: Request) -> User:
    row = db.get_credentials(payload.email)
    if row is None or not auth.verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    request.session["user_id"] = row["id"]
    return db.get_user(row["id"])


@app.post("/api/auth/logout", status_code=204)
def logout(request: Request) -> None:
    request.session.clear()


@app.get("/api/auth/me", response_model=User | None)
def me(request: Request) -> User | None:
    return current_user(request)


# ---------- chat ----------


@app.post("/api/chat", response_model=ChatReply)
async def chat(payload: ChatRequest, request: Request) -> ChatReply:
    user = current_user(request)

    # For a signed-in shopper the stored conversation is the source of truth;
    # a guest's history only exists in their browser, so it comes with the request.
    if user:
        history = [
            ChatTurn(role=row["role"], content=row["content"])
            for row in db.load_history(user.id)
        ]
    else:
        history = payload.history

    # Identity comes from the session, never from the request body.
    customer = (
        Customer(id=user.id, name=user.name, email=user.email, first_name=user.first_name)
        if user
        else None
    )

    # The browser says which page it's on; the product itself is re-read from
    # the catalogue so the agent only ever sees facts the database vouches for.
    page = payload.page
    page_product = db.get_product(page.product_id) if page and page.product_id else None

    try:
        message, products = await agent.reply(
            payload.message,
            history,
            customer=customer,
            page_path=page.path if page else "/",
            page_product=page_product,
        )
    except Exception:
        log.exception("agent run failed")
        raise HTTPException(
            status_code=502,
            detail="The shop assistant is unavailable right now. Please try again.",
        )

    if user:
        db.save_message(user.id, "user", payload.message, None)
        db.save_message(
            user.id,
            "assistant",
            message,
            json.dumps([p.model_dump() for p in products]),
        )

    return ChatReply(message=message, products=products)


@app.get("/api/chat/history", response_model=list[StoredChatTurn])
def chat_history(request: Request) -> list[StoredChatTurn]:
    user = current_user(request)
    if not user:
        return []
    return [
        StoredChatTurn(
            role=row["role"],
            content=row["content"],
            products=json.loads(row["products_json"]) if row["products_json"] else [],
        )
        for row in db.load_history(user.id)
    ]
