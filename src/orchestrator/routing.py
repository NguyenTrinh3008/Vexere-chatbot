"""
Routing logic for LangGraph workflow.
"""

from .types import State

def route_from_classify(state: State) -> str:
    """
    Route based on classified intent and available fields.
    """
    intent = state.get("intent")
    
    # Direct intent routing
    if intent == "check_booking":
        return "check_booking"
    elif intent == "view_trips":
        return "view_trips"
    elif intent == "cancel_booking":
        return "cancel_booking"
    elif intent == "get_invoice":
        return "get_invoice"
    elif intent == "create_complaint":
        return "create_complaint"
    elif intent == "faq":
        return "faq"
    
    # Change time workflow routing
    has_bid  = bool(state.get("booking_id"))
    has_date = bool(state.get("date"))
    has_trip = bool(state.get("trip_id"))

    # If we have any change_time fields, follow the change_time workflow regardless of intent label
    if has_bid or has_date or has_trip:
        if not (has_bid and has_date):
            return "extract"
        if not has_trip:
            return "candidates"
        return "apply"

    # No fields and no recognized intent → fallback
    if intent == "unknown":
        return "fallback"

    # Default safe route
    return "extract"

def route_from_extract(state: State) -> str:
    """Route from extract node based on available fields."""
    # Only proceed when we have both bid & date in state
    if state.get("booking_id") and state.get("date"):
        return "candidates"
    return "end"

def route_from_media_ingest(state: State) -> str:
    """Decide which path to take after media_ingest to avoid double classify runs.
    - If there are attachments and media_type == image → image_vision
    - If there are attachments and media_type == audio → audio_transcribe
    - Otherwise → classify (no media path)
    """
    attachments = state.get("attachments") or []
    media_type = state.get("media_type")
    if attachments:
        if media_type == "image":
            return "image_vision"
        if media_type == "audio":
            return "audio_transcribe"
    return "classify"
