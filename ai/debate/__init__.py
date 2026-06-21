import os
from langchain_anthropic import ChatAnthropic

DEFAULT_MODEL = os.getenv("WALLET_COPILOT_MODEL", "claude-opus-4-8")


def build_llm(model: str | None = DEFAULT_MODEL):
    llm = ChatAnthropic(
        model=model,
        max_tokens=2048,
    )
    return llm


# build_llm 정의 후 import — orchestrator가 `from . import build_llm`로 받기 때문.
from .orchestrator import build_fact_sheet, run_debate  # noqa: E402

__all__ = [
    "build_llm",
    "DEFAULT_MODEL",
    "run_debate",
    "build_fact_sheet",
]
