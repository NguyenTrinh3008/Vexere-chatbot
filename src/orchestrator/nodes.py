"""
LangGraph nodes for handling different user intents.
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage
from src.services.booking_sqlite import BookingServiceSQL
from .types import State
from .utils import fmt_dt_vn, fmt_date_vn_just_day, fmt_fee_vnd, md_candidates_table
from .llm_extractor import extract_fields_llm
from .rag_faq import get_contextual_faq_response

# --- Media processing placeholders (image/audio) ---
def media_ingest_node(state: State) -> State:
    """Detect and ingest media (image/audio). Route text to downstream nodes.
    - If media present, set media_type and keep attachments for later nodes.
    - If no media, no-op.
    """
    attachments = state.get("attachments") or []
    if not attachments:
        return {}
    # Heuristic: assume caller sets media_type already; default to image if unknown
    media_type = state.get("media_type") or "image"
    return {"media_type": media_type, "attachments": attachments}

def image_vision_node(state: State) -> State:
    """Use GPT-4o Vision to extract text and key fields from images (skeleton)."""
    if state.get("media_type") != "image":
        return {}
    # Placeholder: downstream implementation will call GPT-4o on images
    # and populate media_text + structured_entities.
    return {}

def audio_transcribe_node(state: State) -> State:
    """Use Whisper/gpt-4o-mini-transcribe to get transcript from audio (skeleton)."""
    if state.get("media_type") != "audio":
        return {}
    # Placeholder: downstream implementation will transcribe and set media_text.
    return {}

def ticket_parse_node(state: State) -> State:
    """Normalize/validate text from media to structured entities (skeleton)."""
    media_text = state.get("media_text")
    if not media_text:
        return {}
    # Placeholder: downstream will normalize date, map routes, detect booking_id.
    return {}

def merge_media_text_node(state: State) -> State:
    """Merge media_text with last user text so classifier sees unified content."""
    media_text = state.get("media_text")
    if not media_text:
        return {}
    # We append an AIMessage to reflect extracted content for downstream context
    merged_msg = AIMessage(content=f"[MEDIA_EXTRACT]\n{media_text}")
    return {"messages": [merged_msg]}

# Service instance
svc = BookingServiceSQL("src/data/mock.db")

def classify_node(state: State) -> State:
    """
    Classify intent and extract fields using LLM.
    """
    text = state["messages"][-1].content if state.get("messages") else ""
    updates: Dict[str, Any] = {}

    print(f"DEBUG: Analyzing text: '{text}'")
    
    # Use LLM to extract information and classify intent
    fx = extract_fields_llm(text)
    print(f"DEBUG: LLM extracted: {fx}")
    
    # Extract fields from LLM (including intent)
    intent = fx.get("intent")
    bid  = fx.get("booking_id")
    date = fx.get("date")
    trip = fx.get("trip_id")
    route_from = fx.get("route_from")
    route_to = fx.get("route_to")
    complaint_type = fx.get("complaint_type")
    description = fx.get("description")

    # Use intent from LLM (already intelligently classified)
    if intent:
        updates["intent"] = intent
        print(f"DEBUG: Using LLM classified intent: {intent}")
    else:
        # Heuristic default: if we have any change_time signals, default to change_time
        prior_bid = state.get("booking_id")
        prior_date = state.get("date")
        if prior_bid or prior_date or trip:
            updates["intent"] = "change_time"
            print("DEBUG: No intent from LLM; inferring 'change_time' from available fields")
        else:
            updates["intent"] = "unknown"
            print("DEBUG: No intent from LLM, defaulting to unknown")

    # Update fields to state
    if bid:  updates["booking_id"] = bid
    if date: updates["date"] = date
    if trip: updates["trip_id"] = trip
    if route_from: updates["route_from"] = route_from
    if route_to: updates["route_to"] = route_to
    if complaint_type: updates["complaint_type"] = complaint_type
    if description: updates["description"] = description

    return updates

def extract_node(state: State) -> State:
    """Extract missing information for change_time intent."""
    missing = []
    if not state.get("booking_id"):
        missing.append("**mã vé** (ví dụ: `VX123456`)")
    if not state.get("date"):
        missing.append("**ngày muốn đổi** (ví dụ: `2025-09-06`)")

    if missing:
        msg = "⚠️ Thiếu " + " và ".join(missing) + ".\nVui lòng cung cấp để mình tiếp tục."
        return {"messages": [AIMessage(content=msg)]}
    return {}

def candidates_node(state: State) -> State:
    """Show available trip candidates for change_time intent."""
    bid, date = state.get("booking_id"), state.get("date")
    try:
        cands = svc.get_candidates(bid, date)
        # Try to show current trip id for context
        current_trip_id = None
        try:
            current_trip_id = svc.get_current_trip_id(bid)
        except Exception:
            pass
        if not cands:
            msg = (
                f" Hiện **không có chuyến trống** cho ngày **{fmt_date_vn_just_day(date)}**.\n"
                "Bạn có thể thử ngày khác (ví dụ: `2025-09-07`) hoặc khung giờ khác."
            )
            return {"messages": [AIMessage(content=msg)]}

        table = md_candidates_table(cands)
        header = f"✅ **Các lựa chọn khả dụng cho {fmt_date_vn_just_day(date)}**"
        if current_trip_id:
            header += f"\nHiện tại vé của bạn đang ở chuyến: `{current_trip_id}`"
        msg = f"{header}\n\n{table}\n\n👉 Vui lòng trả lời **mã chuyến** bạn muốn (ví dụ: `T001`)."
        return {"messages": [AIMessage(content=msg)]}
    except KeyError:
        return {"messages": [AIMessage(content="Không tìm thấy vé. Vui lòng kiểm tra lại **mã vé**.")]}    

def apply_node(state: State) -> State:
    """Apply trip change for change_time intent."""
    text = state["messages"][-1].content if state.get("messages") else ""
    # Use LLM to extract trip_id from this turn if not already available
    trip_id = state.get("trip_id")
    if not trip_id:
        fx = extract_fields_llm(text)
        trip_id = fx.get("trip_id")

    bid = state.get("booking_id")
    if not trip_id:
        return {"messages": [AIMessage(content="👉 Vui lòng cung cấp **mã chuyến** muốn đổi (ví dụ: `T001`).")]}
    try:
        res = svc.apply_change(bid, trip_id)
        if res.get("status") == "ok":
            if res.get("note") == "no-op":
                msg = (
                    "ℹ **Không có thay đổi**\n"
                    f"- Mã vé: **{res['booking_id']}**\n"
                    f"- Giờ hiện tại: **{fmt_dt_vn(res['new_time'])}**\n"
                    + (f"- Mã chuyến hiện tại: **{res.get('old_trip_id') or res.get('new_trip_id')}**\n" if res.get('old_trip_id') or res.get('new_trip_id') else "")
                    + f"- Phí: **{fmt_fee_vnd(0)}**\n\n"
                    + "Bạn có muốn xem **khung giờ khác** không?"
                )
            else:
                fee_str = fmt_fee_vnd(res.get("fee"))
                msg = (
                    " **Đổi giờ thành công**\n"
                    f"- Mã vé: **{res['booking_id']}**\n"
                    f"- Giờ mới: **{fmt_dt_vn(res['new_time'])}**\n"
                    + (f"- Mã chuyến mới: **{res.get('new_trip_id')}**\n" if res.get('new_trip_id') else "")
                    + (f"- Mã chuyến cũ: **{res.get('old_trip_id')}**\n" if res.get('old_trip_id') else "")
                    + f"- Phí đổi giờ: **{fee_str}**\n\n"
                    + "Vui lòng kiểm tra **SMS/email** để xác nhận."
                )
            return {"trip_id": trip_id, "result": res, "messages": [AIMessage(content=msg)]}
        return {"messages": [AIMessage(content=" Không thể đổi vì **hết chỗ** hoặc lỗi khác. Hãy thử **một chuyến khác**.")]}
    except KeyError as e:
        return {"messages": [AIMessage(content=f" {str(e)}")]}

def check_booking_node(state: State) -> State:
    """Handle check_booking intent."""
    bid = state.get("booking_id")
    
    if not bid:
        return {"messages": [AIMessage(content="👉 Vui lòng cung cấp **mã vé** để kiểm tra thông tin (ví dụ: `VX123456`).")]}
    
    try:
        # Get booking information
        booking = svc.get_booking(bid)
        
        # Get current trip information
        try:
            current_trip = svc.get_current_trip(bid)
            trip_info = f"**Mã chuyến:** `{current_trip['trip_id']}`\n"
        except KeyError:
            trip_info = "**Mã chuyến:** Không tìm thấy\n"
        
        # Format booking information
        msg = (
            "📋 **Thông tin vé hiện tại**\n\n"
            f"**Mã vé:** `{booking['booking_id']}`\n"
            f"**Tuyến:** {booking['route_from']} → {booking['route_to']}\n"
            f"**Giờ khởi hành:** {fmt_dt_vn(booking['depart_time'])}\n"
            f"**Trạng thái:** {booking['status']}\n"
            f"**Hạng ghế:** {booking['seat_class']}\n"
            f"**SĐT:** {booking.get('user_phone', 'Chưa cập nhật')}\n"
            f"{trip_info}\n"
            "💡 Bạn có muốn **đổi giờ** vé này không?"
        )
        
        return {"result": booking, "messages": [AIMessage(content=msg)]}
        
    except KeyError:
        return {"messages": [AIMessage(content=" Không tìm thấy vé với mã `" + bid + "`. Vui lòng kiểm tra lại **mã vé**.")]}
    except Exception as e:
        return {"messages": [AIMessage(content=f" Lỗi khi kiểm tra vé: {str(e)}")]}

def view_trips_node(state: State) -> State:
    """Handle view_trips intent."""
    route_from = state.get("route_from")
    route_to = state.get("route_to")
    date = state.get("date")
    
    # If missing information, ask user
    missing = []
    if not route_from:
        missing.append("**điểm đi** (ví dụ: HCM)")
    if not route_to:
        missing.append("**điểm đến** (ví dụ: Da Lat)")
    if not date:
        missing.append("**ngày** (ví dụ: 2025-09-06)")
    
    if missing:
        msg = "👉 Vui lòng cung cấp " + " và ".join(missing) + " để xem danh sách chuyến."
        return {"messages": [AIMessage(content=msg)]}
    
    try:
        # Call API to get trip list
        import requests
        response = requests.get("http://localhost:8080/trips/available", params={
            "route_from": route_from,
            "route_to": route_to,
            "date": date
        })
        
        if response.status_code == 200:
            data = response.json()
            trips = data.get("trips", [])
            
            if not trips:
                msg = f" **Không có chuyến khả dụng** cho tuyến **{route_from} → {route_to}** ngày **{date}**."
                return {"messages": [AIMessage(content=msg)]}
            
            # Format trip table
            table_rows = ["| Mã chuyến | Giờ xuất phát | Chỗ còn | Giá |", "|---|---:|---:|---:|"]
            for trip in trips:
                table_rows.append(f"| `{trip['trip_id']}` | {fmt_dt_vn(trip['depart_time'])} | {trip['seats_available']} | {fmt_fee_vnd(trip['base_price'])} |")
            
            table = "\n".join(table_rows)
            msg = f"🚌 **Các lựa chọn khả dụng cho {fmt_date_vn_just_day(date)}**\n\n**Tuyến:** {route_from} → {route_to}\n\n{table}\n\n💡 Bạn có muốn **đặt vé** cho chuyến nào không?"
            
            return {"result": data, "messages": [AIMessage(content=msg)]}
        else:
            return {"messages": [AIMessage(content=f"Lỗi khi lấy danh sách chuyến: {response.status_code}")]}
            
    except Exception as e:
        return {"messages": [AIMessage(content=f"Lỗi khi xem chuyến: {str(e)}")]}

def cancel_booking_node(state: State) -> State:
    """Handle cancel_booking intent."""
    booking_id = state.get("booking_id")
    
    if not booking_id:
        return {"messages": [AIMessage(content="👉 Vui lòng cung cấp **mã vé** để hủy (ví dụ: VX123456).")]}
    
    try:
        # Call API to cancel booking
        import requests
        response = requests.post(f"http://localhost:8080/bookings/{booking_id}/cancel")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                msg = f" **Hủy vé thành công**\n\n"
                msg += f"**Mã vé:** {data['booking_id']}\n"
                msg += f"**Giá gốc:** {fmt_fee_vnd(data.get('base_price', 0))}\n"
                msg += f"**Phí đổi giờ:** {fmt_fee_vnd(data.get('change_fee', 0))}\n"
                msg += f"**Tổng tiền hoàn:** {fmt_fee_vnd(data['refund_amount'])}\n"
                msg += f"**Thông báo:** {data['message']}"
                return {"result": data, "messages": [AIMessage(content=msg)]}
            else:
                return {"messages": [AIMessage(content=f" {data.get('reason', 'Không thể hủy vé')}")]}
        else:
            return {"messages": [AIMessage(content=f" Lỗi khi hủy vé: {response.status_code}")]}
            
    except Exception as e:
        return {"messages": [AIMessage(content=f" Lỗi khi hủy vé: {str(e)}")]}

def get_invoice_node(state: State) -> State:
    """Handle get_invoice intent."""
    booking_id = state.get("booking_id")
    
    if not booking_id:
        return {"messages": [AIMessage(content="👉 Vui lòng cung cấp **mã vé** để xuất hóa đơn (ví dụ: VX123456).")]}
    
    try:
        # Call API to get invoice
        import requests
        response = requests.get(f"http://localhost:8080/bookings/{booking_id}/invoice")
        
        if response.status_code == 200:
            data = response.json()
            msg = f"🧾 **Hóa đơn chi tiết**\n\n"
            msg += f"**Mã vé:** {data['booking_id']}\n"
            msg += f"**Tuyến:** {data['route']}\n"
            msg += f"**Giờ khởi hành:** {fmt_dt_vn(data['depart_time'])}\n"
            msg += f"**Hạng ghế:** {data['seat_class']}\n"
            msg += f"**Trạng thái:** {data['status']}\n\n"
            msg += f"**Giá gốc:** {fmt_fee_vnd(data['base_price'])}\n"
            msg += f"**Phí đổi giờ:** {fmt_fee_vnd(data['change_fee'])}\n"
            msg += f"**Tổng cộng:** {fmt_fee_vnd(data['total_amount'])}\n\n"
            msg += f"**Ngày xuất hóa đơn:** {fmt_dt_vn(data['invoice_date'])}"
            return {"result": data, "messages": [AIMessage(content=msg)]}
        else:
            return {"messages": [AIMessage(content=f" Lỗi khi lấy hóa đơn: {response.status_code}")]}
            
    except Exception as e:
        return {"messages": [AIMessage(content=f" Lỗi khi lấy hóa đơn: {str(e)}")]}

def create_complaint_node(state: State) -> State:
    """Handle create_complaint intent."""
    booking_id = state.get("booking_id")
    complaint_type = state.get("complaint_type")
    description = state.get("description")
    
    if not booking_id:
        return {"messages": [AIMessage(content="👉 Vui lòng cung cấp **mã vé** để tạo khiếu nại (ví dụ: VX123456).")]}
    
    if not complaint_type:
        return {"messages": [AIMessage(content="👉 Vui lòng chọn **loại khiếu nại**:\n- **SERVICE**: Về dịch vụ, nhân viên\n- **REFUND**: Về hoàn tiền\n- **CANCELLATION**: Về hủy vé, đổi vé\n- **OTHER**: Vấn đề khác")]}
    
    if not description:
        return {"messages": [AIMessage(content="👉 Vui lòng mô tả **chi tiết khiếu nại** của bạn.")]}
    
    try:
        # Call API to create complaint
        import requests
        response = requests.post(
            f"http://localhost:8080/complaints",
            params={
                "booking_id": booking_id,
                "complaint_type": complaint_type,
                "description": description
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            msg = f"📝 **Khiếu nại đã được ghi nhận**\n\n"
            msg += f"**Mã khiếu nại:** #{data['complaint_id']}\n"
            msg += f"**Mã vé:** {data['booking_id']}\n"
            msg += f"**Loại:** {data['complaint_type']}\n"
            msg += f"**Mô tả:** {data['description']}\n"
            msg += f"**Trạng thái:** {data['status']}\n"
            msg += f"**Thời gian:** {fmt_dt_vn(data['created_at'])}\n\n"
            msg += f"**Thông báo:** {data['message']}"
            return {"result": data, "messages": [AIMessage(content=msg)]}
        else:
            return {"messages": [AIMessage(content=f" Lỗi khi tạo khiếu nại: {response.status_code}")]}
            
    except Exception as e:
        return {"messages": [AIMessage(content=f" Lỗi khi tạo khiếu nại: {str(e)}")]}

def faq_node(state: State) -> State:
    """Handle FAQ intent using RAG system."""
    text = state["messages"][-1].content if state.get("messages") else ""
    
    if not text:
        return {"messages": [AIMessage(content="Xin lỗi, tôi không hiểu câu hỏi của bạn. Vui lòng hỏi lại.")]}
    
    try:
        # Get contextual FAQ response using RAG
        response = get_contextual_faq_response(text)
        
        # Format the response
        msg = f" **Câu hỏi thường gặp**\n\n{response}"
        
        return {"messages": [AIMessage(content=msg)]}
        
    except Exception as e:
        return {"messages": [AIMessage(content=f" Lỗi khi tìm kiếm thông tin: {str(e)}")]}

def fallback_node(state: State) -> State:
    """Handle unknown intents with helpful suggestions."""
    return {"messages": [AIMessage(content="Hiện mình hỗ trợ:\n- **Kiểm tra vé:** _\"Kiểm tra vé VX123456\"_\n- **Đổi giờ:** _\"Mình muốn đổi giờ vé VX123456 sang 06/09\"_\n- **Xem chuyến:** _\"Xem chuyến từ HCM đến Da Lat ngày 6/9\"_\n- **Hủy vé:** _\"Hủy vé VX123456\"_\n- **Xuất hóa đơn:** _\"Xuất hóa đơn VX123456\"_\n- **Khiếu nại:** _\"Tôi muốn khiếu nại về vé VX123456\"_\n- **Câu hỏi thường gặp:** _\"Làm thế nào để đặt vé?\"_")]}
