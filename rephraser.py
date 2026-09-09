"""Step 1: rephrase the raw user question into a clean, standalone question.
Resolves company names to tickers where obvious, fixes typos, and later
(once chat memory exists) folds prior context into a standalone question."""

import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

REPHRASE_MODEL = os.environ.get("REPHRASE_MODEL", "openai/gpt-oss-20b")

SYSTEM_PROMPT = """You rewrite user questions about stocks and ETFs into a single, clear, standalone question.
- Resolve company names to their stock ticker symbol when obvious (e.g. "apple" -> AAPL).
- Fix typos and remove filler words.
- If conversation history is provided and the question depends on it (e.g. "what about its high?"), \
fold that context into a standalone question.
- Output ONLY the rewritten question, nothing else."""


def rephrase(user_question: str, chat_history: list[dict] | None = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if chat_history:
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in chat_history[-6:])
        messages.append({
            "role": "user",
            "content": f"Conversation so far:\n{history_text}\n\nLatest question: {user_question}",
        })
    else:
        messages.append({"role": "user", "content": user_question})

    response = client.chat.completions.create(
        model=REPHRASE_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=100,
    )
    if not response.choices:
        return user_question.strip()

    content = response.choices[0].message.content
    return content.strip() if content else user_question.strip()