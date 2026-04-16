# Cost per 1K tokens (USD) for all models available on the LiteLLM proxy.
# Prices are approximate — update this dict when models change.
# Models listed: GET /v1/models on proxy (March 2026).
MODEL_PRICES: dict[str, dict[str, float]] = {
    "gpt-5":        {"input": 0.015, "output": 0.060},
    "gpt-5-codex":  {"input": 0.015, "output": 0.060},
    "gpt-5.1":      {"input": 0.005, "output": 0.015},
    "gpt-5.4-pro":  {"input": 0.010, "output": 0.030},
    "gpt-5.4":      {"input": 0.005, "output": 0.015},
    "gpt-5.4-mini": {"input": 0.002, "output": 0.008},
    "gpt-5-mini":   {"input": 0.002, "output": 0.008},
    "gpt-5.4-nano": {"input": 0.001, "output": 0.004},
}

# Fallback used when a model is not in MODEL_PRICES
_DEFAULT_PRICES: dict[str, float] = {"input": 0.005, "output": 0.015}


class CostTrackingMixin:

    def __init__(self):
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._total_cost: float = 0.0

    def track_usage(self, response, model: str = "") -> dict:
        prices = MODEL_PRICES.get(model, _DEFAULT_PRICES)
        usage = getattr(response, "usage_metadata", None) or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = (input_tokens / 1000 * prices["input"]) + \
               (output_tokens / 1000 * prices["output"])
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self._total_cost += cost
        return {
            "model": model or "unknown",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
        }

    def get_cost_summary(self) -> dict:
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_cost_usd": round(self._total_cost, 6),
        }
