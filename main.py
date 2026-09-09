from dotenv import load_dotenv
import logging
from time import perf_counter
from typing import Literal
from pathlib import Path

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent import run_agent

app = FastAPI(title="Stock/ETF Agent")
FRONTEND_PATH = Path(__file__).parent / "frontend" / "index.html"
LOG_PATH = FRONTEND_PATH.parent.parent / "logs" / "agent_actions.txt"
LOG_PATH.parent.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
)
logger = logging.getLogger("stockbot.actions")
app.mount("/static", StaticFiles(directory=FRONTEND_PATH.parent), name="static")


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_PATH)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class QueryRequest(BaseModel):
    question: str
    history: list[ChatMessage] | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(req: QueryRequest):
    request_started = perf_counter()
    history = [message.model_dump() for message in req.history] if req.history else None
    logger.info("action=request_received history_messages=%d", len(history or []))
    try:
        agent_started = perf_counter()
        answer = run_agent(req.question, history)
        agent_ms = (perf_counter() - agent_started) * 1000
        logger.info("action=answer_completed")
    except Exception as error:
        total_ms = (perf_counter() - request_started) * 1000
        logger.exception("action=request_failed error=%s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error

    total_ms = (perf_counter() - request_started) * 1000
    return {
        "original_question": req.question,
        "rephrased_question": req.question,
        "answer": answer,
        "timing_seconds": {
            "agent": round(agent_ms / 1000, 2),
            "total": round(total_ms / 1000, 2),
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)