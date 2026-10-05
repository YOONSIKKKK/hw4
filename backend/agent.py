"""Campus Customs shop assistant — PydanticAI agent wiring.

The system prompt lives in prompts/prompt.md and is loaded at import time.
The model is Claude Opus 5, reached through Portkey's OpenAI-compatible API.
"""

import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import audit
from models import ChatTurn, Product
from tools import TOOLS, Customer, ShopDeps

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

# A clone keeps its .env at the project root; this checkout inherits one from
# the course folder above it. Prefer the project's own.
PROJECT_ENV = PROJECT_DIR / ".env"
ROOT_ENV = PROJECT_ENV if PROJECT_ENV.exists() else PROJECT_DIR.parent / ".env"

MODEL_NAME = "claude-opus-5"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# One shopper message may bounce round the think→tool→think loop a few times.
# Six model requests is comfortably more than any real question needs (the
# busiest observed is three) and stops a confused run from spending money in a
# circle. Exceeding it ends the turn with a plain apology, not a crash.
MAX_MODEL_REQUESTS = 6
TOOL_RETRIES = 2

LOOP_LIMIT_REPLY = (
    "Sorry — I got tangled up looking that one up. Could you try asking it a different way?"
)

load_dotenv(ROOT_ENV)

SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


def _build_model() -> OpenAIChatModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError(f"PORTKEY_API_KEY not found in {ROOT_ENV}")
    return OpenAIChatModel(
        MODEL_NAME,
        provider=OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key),
    )


agent = Agent(
    _build_model(),
    deps_type=ShopDeps,
    instructions=SYSTEM_PROMPT,
    tools=TOOLS,
    retries=TOOL_RETRIES,
)


@agent.instructions
def who_is_shopping(ctx: RunContext[ShopDeps]) -> str:
    """Who the agent is talking to. Injected per request, never recalled."""
    customer = ctx.deps.customer
    if customer is None:
        return (
            "The shopper is browsing as a guest — they are not signed in, so you don't know "
            "their name and this conversation won't be remembered after they leave. Don't ask "
            "them to log in unless it's relevant."
        )
    return (
        "The shopper is signed in to their Campus Customs account. "
        f"Full name: {customer.name}. "
        f"First name: {customer.first_name or customer.name.split()[0]}. "
        f"Email on the account: {customer.email}. "
        "Greet them by first name and use it occasionally. Their email is here only so you can "
        "confirm which account they're signed in to if they ask — don't volunteer it, don't "
        "repeat it back unprompted, and never put it in a list or summary."
    )


@agent.instructions
def what_they_are_looking_at(ctx: RunContext[ShopDeps]) -> str:
    """The page the shopper is on, so 'this one' resolves without a guess."""
    product = ctx.deps.page_product
    if product is not None:
        in_stock = [i.size for i in product.inventory if i.quantity > 0]
        return (
            "RIGHT NOW the shopper is looking at this product's page, so 'this', 'this one', "
            "'it' and 'the one I'm looking at' mean this item unless they clearly mean "
            "something else:\n"
            f"- product_id: {product.product_id}\n"
            f"- name: {product.name} ({product.garment_type})\n"
            f"- price: ${product.price:.2f}\n"
            f"- colors: {', '.join(product.colors)}\n"
            f"- sizes in stock: {', '.join(in_stock) if in_stock else 'none — sold out'}\n"
            "These facts are current. For anything beyond them, use your tools with that "
            "product_id."
        )
    locations = {
        "/": "the home page",
        "/products": "the full product listing",
        "/about": "the About Us page",
        "/login": "the log-in page",
        "/create-account": "the create-account page",
    }
    where = locations.get(ctx.deps.page_path)
    if where:
        return f"The shopper is on {where}."
    return ""


def _to_model_messages(history: list[ChatTurn]) -> list[ModelMessage]:
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


BLOCKED_REPLY = (
    "I'd rather not go into that one — but I'm happy to help you find Yale gear. "
    "What are you shopping for?"
)


async def reply(
    message: str,
    history: list[ChatTurn],
    customer: Customer | None = None,
    page_path: str = "/",
    page_product: Product | None = None,
) -> tuple[str, list[Product]]:
    """Answer one shopper message. Returns the reply and the products its tools surfaced."""
    run_id = uuid.uuid4().hex[:8]
    started = time.perf_counter()
    deps = ShopDeps(
        customer=customer,
        page_path=page_path,
        page_product=page_product,
        run_id=run_id,
    )

    audit.record(
        "run_start",
        run_id=run_id,
        model=MODEL_NAME,
        signed_in=customer is not None,
        page=page_path,
        page_product=page_product.product_id if page_product else None,
        history_turns=len(history),
        message=audit.brief(message),
    )

    def finish(stop_reason: str, **extra) -> None:
        audit.record(
            "run_end",
            run_id=run_id,
            stop_reason=stop_reason,
            tool_calls=deps.tool_calls,
            products_shown=len(deps.shown),
            ms=round((time.perf_counter() - started) * 1000, 1),
            **extra,
        )

    try:
        result = await agent.run(
            message,
            deps=deps,
            message_history=_to_model_messages(history),
            usage_limits=UsageLimits(request_limit=MAX_MODEL_REQUESTS),
        )
    except UsageLimitExceeded:
        finish("loop_limit_reached", limit=MAX_MODEL_REQUESTS)
        return LOOP_LIMIT_REPLY, deps.shown
    except ModelHTTPError as exc:
        # The provider's own filter rejected the prompt. A shopper should get a
        # polite decline in the chat, not a broken widget.
        if exc.status_code == 400 and "content_filter" in str(exc.body):
            finish("blocked_by_content_filter")
            return BLOCKED_REPLY, []
        finish("model_http_error", detail=audit.brief(str(exc)))
        raise
    except Exception as exc:
        finish("error", detail=audit.brief(repr(exc)))
        raise

    finish("final_response", reply=audit.brief(result.output))
    return result.output, deps.shown
