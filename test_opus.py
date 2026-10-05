"""Portkey smoke test for Claude Opus 5."""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ROOT_ENV)

client = OpenAI(
    api_key=os.environ["PORTKEY_API_KEY"],
    base_url="https://api.portkey.ai/v1",
)

response = client.responses.create(
    model="claude-opus-5",
    input="Reply with exactly: Opus 5 test works!",
)

print(response.output_text)
