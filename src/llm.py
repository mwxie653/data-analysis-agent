"""DeepSeek API client via OpenAI-compatible interface."""

import os
from openai import OpenAI

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekClient:
    """Wraps the DeepSeek API for Agent tool calling."""

    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError("DEEPSEEK_API_KEY is required. Set it in .env or pass directly.")
        self.client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)
