# app/chat_api.py
from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any, Dict

from langchain_core.messages import HumanMessage
from src.orchestrator import app_graph  # đã compile sẵn với memory

app = FastAPI(title="Chat Orchestrator API")

class ChatIn(BaseModel):
    message: str
    thread_id: Optional[str] = "demo1"

class ChatOut(BaseModel):
    reply: str
    # Một số state hữu ích để debug UI
    intent: Optional[str] = None
    booking_id: Optional[str] = None
    date: Optional[str] = None
    trip_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn):
    # Giữ “tiến trình hội thoại” theo thread_id
    config = {"configurable": {"thread_id": body.thread_id or "default"}}

    # Gửi message người dùng vào graph
    out = app_graph.invoke({"messages": [HumanMessage(content=body.message)]}, config)

    # Lấy câu trả lời cuối cùng (được LangGraph + LLM tạo ở node tương ứng)
    reply = ""
    if "messages" in out and out["messages"]:
        reply = out["messages"][-1].content

    return ChatOut(
        reply=reply,
        intent=out.get("intent"),
        booking_id=out.get("booking_id"),
        date=out.get("date"),
        trip_id=out.get("trip_id"),
        result=out.get("result"),
        error=out.get("error"),
    )
