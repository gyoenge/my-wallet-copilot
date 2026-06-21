import os 
from langchain_anthropic import ChatAnthropic


DEFAULT_MODEL = os.getenv("WALLET_COPILOT_MODEL", "claude-opus-4-8")

def build_llm(model: str | None = DEFAULT_MODEL): 
    llm = ChatAnthropic(
        model=model, 
        max_tokens=2048, 
    )
    return llm 


__all__ = [
    "build_llm",
    "DEFAULT_MODEL",
]