"""Fake LLM client. Mirrors a real provider: when the model hits the token limit it
returns finish_reason='length' with a truncated answer."""


class MaxTokensExceeded(Exception):
    def __init__(self, max_tokens: int, prompt_tokens: int):
        super().__init__(f"completion hit max_tokens={max_tokens} (prompt_tokens={prompt_tokens})")
        self.max_tokens = max_tokens
        self.prompt_tokens = prompt_tokens


def count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def complete(prompt: str, max_tokens: int = 256) -> dict:
    prompt_tokens = count_tokens(prompt)
    # The model "wants" to write roughly as many tokens as the prompt has.
    wanted = prompt_tokens
    if wanted > max_tokens:
        raise MaxTokensExceeded(max_tokens, prompt_tokens)
    return {"text": "ok: " + prompt[:40], "finish_reason": "stop", "completion_tokens": wanted}
