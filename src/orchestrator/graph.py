"""
LangGraph workflow definition and compilation.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from .types import State
from .nodes import (
    classify_node, extract_node, candidates_node, apply_node,
    check_booking_node, view_trips_node, cancel_booking_node,
    get_invoice_node, create_complaint_node, faq_node, fallback_node,
    media_ingest_node, image_vision_node, audio_transcribe_node,
    ticket_parse_node, merge_media_text_node
)
from .routing import route_from_classify, route_from_extract, route_from_media_ingest

def create_graph() -> StateGraph:
    """Create and configure the LangGraph workflow."""
    graph = StateGraph(State)
    
    # Add nodes
    graph.add_node("media_ingest", media_ingest_node)
    graph.add_node("image_vision", image_vision_node)
    graph.add_node("audio_transcribe", audio_transcribe_node)
    graph.add_node("ticket_parse", ticket_parse_node)
    graph.add_node("merge_media_text", merge_media_text_node)
    graph.add_node("classify", classify_node)
    graph.add_node("extract", extract_node)
    graph.add_node("candidates", candidates_node)
    graph.add_node("apply", apply_node)
    graph.add_node("check_booking", check_booking_node)
    graph.add_node("view_trips", view_trips_node)
    graph.add_node("cancel_booking", cancel_booking_node)
    graph.add_node("get_invoice", get_invoice_node)
    graph.add_node("create_complaint", create_complaint_node)
    graph.add_node("faq", faq_node)
    graph.add_node("fallback", fallback_node)

    # Add edges
    # Start → media ingest → (image/audio parsing) → merge → classify
    graph.add_edge(START, "media_ingest")
    graph.add_conditional_edges("media_ingest", route_from_media_ingest, {
        "image_vision": "image_vision",
        "audio_transcribe": "audio_transcribe",
        "classify": "classify",
    })
    graph.add_edge("image_vision", "ticket_parse")
    graph.add_edge("audio_transcribe", "ticket_parse")
    graph.add_edge("ticket_parse", "merge_media_text")
    graph.add_edge("merge_media_text", "classify")
    # Paths after media processing

    # Conditional edges from classify
    graph.add_conditional_edges(
        "classify",
        route_from_classify,
        {
            "extract": "extract", 
            "candidates": "candidates", 
            "apply": "apply", 
            "check_booking": "check_booking", 
            "view_trips": "view_trips", 
            "cancel_booking": "cancel_booking", 
            "get_invoice": "get_invoice", 
            "create_complaint": "create_complaint",
            "faq": "faq",
            "fallback": "fallback"
        },
    )

    # Conditional edges from extract
    graph.add_conditional_edges(
        "extract",
        route_from_extract,
        {"candidates": "candidates", "end": END},
    )

    # Terminal edges
    graph.add_edge("candidates", END)
    graph.add_edge("apply", END)
    graph.add_edge("check_booking", END)
    graph.add_edge("view_trips", END)
    graph.add_edge("cancel_booking", END)
    graph.add_edge("get_invoice", END)
    graph.add_edge("create_complaint", END)
    graph.add_edge("faq", END)
    graph.add_edge("fallback", END)

    return graph

def compile_graph() -> StateGraph:
    """Compile the graph with memory checkpointing."""
    graph = create_graph()
    memory = InMemorySaver()
    return graph.compile(checkpointer=memory)
