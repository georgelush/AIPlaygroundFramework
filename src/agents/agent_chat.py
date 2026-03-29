"""
Agent 2 — Chat Agent
Pattern: Single-node StateGraph with in-session memory.
Teaches: StateGraph, START, END, MessagesState, MemorySaver, thread_id.
"""

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage
from src.config import LLM_MODEL, LLM_PROXY, LLM_API_KEY, langfuse_handler
from langchain_openai import ChatOpenAI

AGENT_NAME = "Chat Agent"
AGENT_TYPE = "chat"