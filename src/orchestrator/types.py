"""
Type definitions and state management for the orchestrator.
"""

from typing import Annotated, Optional, Literal, List
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

class State(TypedDict, total=False):
    """State definition for LangGraph workflow."""
    messages: Annotated[List[AnyMessage], add_messages]
    intent: Literal["change_time", "check_booking", "view_trips", "cancel_booking", "get_invoice", "create_complaint", "faq", "unknown"]
    booking_id: Optional[str]
    date: Optional[str]   # YYYY-MM-DD
    trip_id: Optional[str]
    route_from: Optional[str]  # Điểm đi
    route_to: Optional[str]    # Điểm đến
    complaint_type: Optional[str]  # Loại khiếu nại
    description: Optional[str]     # Mô tả khiếu nại
    # Media ingestion (image/audio) support
    media_type: Optional[str]          # image | audio | none
    attachments: Optional[list]        # danh sách URL/base64 của media
    media_text: Optional[str]          # text trích xuất từ ảnh/âm thanh
    structured_entities: Optional[dict]  # dữ liệu cấu trúc từ media (booking_id, date, route, ...)
    result: Optional[dict]
    error: Optional[str]
