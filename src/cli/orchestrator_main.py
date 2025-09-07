# orchestrator_main.py
"""
Main orchestrator file - refactored and simplified.
This is the entry point that replaces the original orchestrator_langgraph.py
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, AIMessage
from orchestrator import app_graph, State

def run_cli(thread_id: str = "demo1") -> None:
    """CLI demo function."""
    print("=== Demo đổi giờ (LangGraph + LLM-only extraction). Gõ 'q' để thoát. ===")
    config = {"configurable": {"thread_id": thread_id}}
    while True:
        txt = input("Bạn: ").strip()
        if txt.lower() in {"q", "quit", "exit"}:
            break
        events = app_graph.stream({"messages": [HumanMessage(content=txt)]}, config, stream_mode="values")
        last = None
        for ev in events:
            last = ev
        if last and "messages" in last:
            print("Bot:", last["messages"][-1].content)
        else:
            print("Bot: (không có phản hồi)")

if __name__ == "__main__":
    run_cli()
