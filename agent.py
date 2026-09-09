"""The LLM router/summarizer. Given a clean question, the model
either answers directly or calls the price tool, then produces the final answer."""

import json
import logging
import os
from openai import OpenAI
from tools.etf_profile import get_etf_profile
from tools.holdings import get_holdings
from tools.price import get_price

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

AGENT_MODEL = os.environ.get("AGENT_MODEL", "anthropic/claude-sonnet-4.5")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_price",
            "description": "Get the latest price and daily change for a stock or ETF ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock or ETF ticker symbol, e.g. AAPL, VOO",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_etf_profile",
            "description": "Get descriptive information and reported fee and performance fields for an ETF.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "ETF ticker symbol, such as VFV, VOO, or VEQT",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_holdings",
            "description": "Get the largest reported holdings of an ETF.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "ETF ticker symbol, such as VFV, VOO, or VEQT",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of holdings to return, from 1 to 25",
                        "minimum": 1,
                        "maximum": 25,
                    },
                },
                "required": ["ticker"],
            },
        },
    },
]

AVAILABLE_TOOLS = {
    "get_price": get_price,
    "get_etf_profile": get_etf_profile,
    "get_holdings": get_holdings,
}
logger = logging.getLogger("stockbot.actions")

SYSTEM_PROMPT = """You are a specialized stock and ETF assistant.

Scope:
- Answer questions about stocks, ETFs, exchanges, market terminology, investing concepts,
    portfolio basics, diversification, fees, dividends, valuation, risk, and investment strategies.
- Explain finance terminology in clear language for the user's apparent level of knowledge.
- You may help users explore investments based on goals, time horizon, risk tolerance, and preferences,
    but provide educational information and candidates to research, not personalized financial advice.

Boundaries:
- Do not answer unrelated questions about topics such as coding, news, travel, entertainment,
    medical care, law, or general trivia. Reply: "I can only help with stocks, ETFs, and investing topics."
- Do not promise returns or claim that an investment is guaranteed or definitely the best choice.
- State important assumptions, risks, fees, and uncertainty when discussing an investment.
- Do not invent prices, performance, holdings, expense ratios, or other current facts.
    Use an available tool when current market data is required. If the required data is unavailable,
    say so clearly.
- Ask a focused follow-up question when the user's goal, country, time horizon, or risk tolerance
    is necessary to give a useful educational response.

Tool use:
- Use the get_price tool whenever the user asks about a current price, daily change, or current value
    of a specific stock or ETF.
- Use get_etf_profile whenever the user asks what an ETF is, its objective, provider, fees, assets,
    yield, exchange, currency, or other profile details.
- Use get_holdings whenever the user asks what an ETF owns, its largest positions, or its holdings.
- Do not use get_price for unrelated questions or when no specific ticker can be identified.

Response style:
- Be concise, clear, neutral, and helpful.
- Use the ticker and company/fund name when known.
- Distinguish factual data from general explanation and opinion."""

MAX_TOOL_ITERATIONS = 4


def run_agent(question: str, chat_history: list[dict] | None = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if chat_history:
        messages.extend(chat_history[-10:])
    messages.append({"role": "user", "content": question})

    for iteration in range(1, MAX_TOOL_ITERATIONS + 1):
        logger.info("action=model_request iteration=%d", iteration)
        response = client.chat.completions.create(
            model=AGENT_MODEL,
            messages=messages,
            tools=TOOLS,
            temperature=0.2,
        )
        if not response.choices:
            error = getattr(response, "error", None)
            logger.error("action=model_empty_response iteration=%d", iteration)
            raise RuntimeError(
                f"The agent model returned no choices. Provider error: {error or response}"
            )
        msg = response.choices[0].message

        if not msg.tool_calls:
            logger.info("action=final_answer iteration=%d", iteration)
            return msg.content

        messages.append(msg.model_dump(exclude_none=True))

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            logger.info("action=tool_call tool=%s ticker=%s", fn_name, args.get("ticker", ""))
            result = AVAILABLE_TOOLS[fn_name](**args)
            logger.info("action=tool_completed tool=%s", fn_name)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    logger.warning("action=max_iterations_reached")
    return "Sorry, I couldn't complete that request."