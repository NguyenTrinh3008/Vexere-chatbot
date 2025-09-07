from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from src.services.booking_sqlite import BookingServiceSQL

app = FastAPI(title="Mock Booking API (SQLite)")
svc = BookingServiceSQL("src/data/mock.db")

@app.get("/")
def root():
    return {
        "message": "Mock Booking API (SQLite)",
        "version": "1.0.0",
        "endpoints": {
            "GET /bookings/{bid}": "Get booking details",
            "GET /bookings/{bid}/candidates": "Get available trip candidates for a date",
            "GET /trips/available": "Get all available trips for a specific date and route",
            "POST /bookings/{bid}/quote": "Get quote for booking change",
            "POST /bookings/{bid}/apply": "Apply booking change",
            "POST /change-time": "Change booking time with booking_id, date, and trip_id"
        },
        "docs": "/docs"
    }

class QuoteIn(BaseModel):
    target_time: datetime

class ApplyIn(BaseModel):
    trip_id: str

class ChangeIn(BaseModel):
    booking_id: str
    date: str         # "2025-09-06"
    trip_id: str      # ví dụ chọn T001 sau khi gọi /candidates

@app.get("/bookings/{bid}")
def get_booking(bid: str):
    try:
        return svc.get_booking(bid)
    except KeyError:
        raise HTTPException(404, "Booking not found")

@app.get("/bookings/{bid}/candidates")
def candidates(bid: str, date: str):
    try:
        return svc.get_candidates(bid, date)
    except KeyError:
        raise HTTPException(404, "Booking not found")

@app.post("/bookings/{bid}/quote")
def quote(bid: str, body: QuoteIn):
    return svc.quote_change(bid, body.target_time)

@app.post("/bookings/{bid}/apply")
def apply(bid: str, body: ApplyIn):
    res = svc.apply_change(bid, body.trip_id)
    if res.get("status") == "fail":
        raise HTTPException(409, res.get("reason", "cannot apply"))
    return res

@app.get("/trips/available")
def get_available_trips(route_from: str, route_to: str, date: str):
    """
    Lấy danh sách các chuyến khả dụng cho một tuyến và ngày cụ thể.
    
    Args:
        route_from: Điểm đi (ví dụ: HCM)
        route_to: Điểm đến (ví dụ: Da Lat)
        date: Ngày (format: YYYY-MM-DD, ví dụ: 2025-09-06)
    
    Returns:
        Danh sách các chuyến khả dụng với thông tin chi tiết
    """
    try:
        trips = svc.get_available_trips(route_from, route_to, date)
        return {
            "route_from": route_from,
            "route_to": route_to,
            "date": date,
            "trips": trips,
            "total_trips": len(trips)
        }
    except Exception as e:
        raise HTTPException(400, f"Error getting available trips: {str(e)}")

@app.post("/change-time")
def change_time(body: ChangeIn):
    # Thực tế: bạn có thể gọi /candidates trước cho UI, ở đây coi như đã chọn trip_id
    return svc.apply_change(body.booking_id, body.trip_id)

@app.post("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: str):
    """
    Hủy vé và trả lại slot cho chuyến.
    
    Args:
        booking_id: Mã vé cần hủy (ví dụ: VX123456)
    
    Returns:
        Thông tin hủy vé và hoàn tiền
    """
    try:
        result = svc.cancel_booking(booking_id)
        return result
    except KeyError:
        raise HTTPException(404, "Booking not found")
    except Exception as e:
        raise HTTPException(400, f"Error canceling booking: {str(e)}")

@app.get("/bookings/{booking_id}/invoice")
def get_invoice(booking_id: str):
    """
    Lấy thông tin hóa đơn chi tiết.
    
    Args:
        booking_id: Mã vé (ví dụ: VX123456)
    
    Returns:
        Thông tin hóa đơn bao gồm giá gốc, phí đổi giờ, tổng tiền
    """
    try:
        invoice = svc.get_invoice(booking_id)
        return invoice
    except KeyError:
        raise HTTPException(404, "Booking not found")
    except Exception as e:
        raise HTTPException(400, f"Error getting invoice: {str(e)}")

@app.post("/complaints")
def create_complaint(booking_id: str, complaint_type: str, description: str):
    """
    Tạo khiếu nại mới.
    
    Args:
        booking_id: Mã vé liên quan (ví dụ: VX123456)
        complaint_type: Loại khiếu nại (SERVICE, REFUND, CANCELLATION, OTHER)
        description: Mô tả chi tiết khiếu nại
    
    Returns:
        Thông tin khiếu nại đã tạo
    """
    try:
        complaint = svc.create_complaint(booking_id, complaint_type, description)
        return complaint
    except KeyError:
        raise HTTPException(404, "Booking not found")
    except Exception as e:
        raise HTTPException(400, f"Error creating complaint: {str(e)}")
