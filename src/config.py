"""
src/config.py - Reads variables from .env and exposes them as constants.
Also creates ready-to-use LLM client and Langfuse callback handler.
"""
import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from langfuse.langchain import CallbackHandler

# Framework-wide logging — set level=WARNING to silence in production
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Silence noisy third-party loggers
logging.getLogger("redisvl").setLevel(logging.WARNING)
logging.getLogger("langgraph.checkpoint.redis").setLevel(logging.WARNING)

load_dotenv()

# LLM
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_PROXY = os.environ.get("LLM_PROXY")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5.4-nano")

# Infrastructure
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Langfuse (observability / tracing)
# langfuse.langchain.CallbackHandler reads these env vars automatically:
# LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
LANGFUSE_PROXY = os.environ.get("LANGFUSE_PROXY")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")

# Set LANGFUSE_HOST so the SDK picks it up automatically
os.environ["LANGFUSE_HOST"] = LANGFUSE_PROXY or ""
os.environ["LANGFUSE_PUBLIC_KEY"] = LANGFUSE_PUBLIC_KEY or ""
os.environ["LANGFUSE_SECRET_KEY"] = LANGFUSE_SECRET_KEY or ""

# Ready-to-use LLM client (LiteLLM proxy, OpenAI-compatible)
llm_client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_PROXY,
)

# Ready-to-use Langfuse callback handler
# In v4, reads LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST from env
langfuse_handler = CallbackHandler()


def get_llm_temperature(llm, configured=None) -> str:
    """Returns temperature display string for trace logs.
    If the model does not support temperature, shows the configured value instead."""
    if not getattr(llm, "profile", {}).get("temperature", True):
        return str(configured) if configured is not None else "default"
    t = llm.temperature
    return str(t) if t is not None else "default"
