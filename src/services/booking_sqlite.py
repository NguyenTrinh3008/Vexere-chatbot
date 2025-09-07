# services/booking_sqlite.py
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict

CUT_OFF_HOURS = 2
FEE_SAME_DAY = 50_000
FEE_DIFF_DAY = 100_000

def _row_to_dict(row: sqlite3.Row) -> Dict:
    return {k: row[k] for k in row.keys()}

class BookingServiceSQL:
    def __init__(self, db_path: str = "mock.db"):
        self.db_path = db_path

    def _con(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        return con

    def get_booking(self, bid: str) -> Dict:
        with self._con() as con:
            r = con.execute("SELECT * FROM bookings WHERE booking_id=?;", (bid,)).fetchone()
            if not r: raise KeyError("Booking not found")
            return _row_to_dict(r)

    def get_candidates(self, bid: str, date: str) -> List[Dict]:
        b = self.get_booking(bid)
        with self._con() as con:
            cur = con.execute("""
                SELECT trip_id, depart_time, seats_available, base_price
                FROM trips
                WHERE route_from=? AND route_to=? AND substr(depart_time,1,10)=? AND seats_available>0
                ORDER BY depart_time
            """, (b["route_from"], b["route_to"], date))
            return [_row_to_dict(x) for x in cur.fetchall()]

    def get_current_trip(self, bid: str) -> Dict:
        """Return the current trip row for the booking (by matching route and depart_time)."""
        b = self.get_booking(bid)
        with self._con() as con:
            r = con.execute(
                """
                SELECT * FROM trips
                WHERE route_from=? AND route_to=? AND depart_time=?
                LIMIT 1
                """,
                (b["route_from"], b["route_to"], b["depart_time"]),
            ).fetchone()
            if not r:
                raise KeyError("Current trip not found")
            return _row_to_dict(r)

    def get_current_trip_id(self, bid: str) -> str:
        return self.get_current_trip(bid)["trip_id"]

    def get_available_trips(self, route_from: str, route_to: str, date: str) -> List[Dict]:
        """
        Lấy danh sách các chuyến khả dụng cho một tuyến và ngày cụ thể.
        
        Args:
            route_from: Điểm đi (ví dụ: HCM)
            route_to: Điểm đến (ví dụ: Da Lat)
            date: Ngày (format: YYYY-MM-DD, ví dụ: 2025-09-06)
        
        Returns:
            Danh sách các chuyến khả dụng với thông tin chi tiết
        """
        with self._con() as con:
            cur = con.execute("""
                SELECT trip_id, depart_time, seats_available, base_price, seats_total
                FROM trips
                WHERE route_from=? AND route_to=? AND substr(depart_time,1,10)=? AND seats_available>0
                ORDER BY depart_time
            """, (route_from, route_to, date))
            return [_row_to_dict(x) for x in cur.fetchall()]

    def quote_change(self, bid: str, target_time: datetime) -> Dict:
        b = self.get_booking(bid)
        now = datetime(2025, 9, 2, 9, 0)  # cố định để test ổn định
        depart = datetime.fromisoformat(b["depart_time"])
        if b["status"] != "PAID":
            return {"allowed": False, "fee": 0, "reason": "Vé không hợp lệ để đổi"}
        if depart - now <= timedelta(hours=CUT_OFF_HOURS):
            return {"allowed": False, "fee": 0, "reason": "Quá hạn đổi"}
        fee = FEE_SAME_DAY if target_time.date() == depart.date() else FEE_DIFF_DAY
        return {"allowed": True, "fee": fee, "new_time": target_time.isoformat()}

    def apply_change(self, bid: str, trip_id: str) -> Dict:
        with self._con() as con:
            con.execute("BEGIN")
            b = con.execute("SELECT * FROM bookings WHERE booking_id=?;", (bid,)).fetchone()
            if not b: con.execute("ROLLBACK"); raise KeyError("Booking not found")
            t = con.execute("SELECT * FROM trips WHERE trip_id=?;", (trip_id,)).fetchone()
            if not t: con.execute("ROLLBACK"); raise KeyError("Trip not found")
            if t["seats_available"] <= 0:
                con.execute("ROLLBACK"); return {"status": "fail", "reason": "Hết chỗ"}

            # find old trip id
            old_trip = con.execute(
                "SELECT * FROM trips WHERE route_from=? AND route_to=? AND depart_time=? LIMIT 1;",
                (b["route_from"], b["route_to"], b["depart_time"]),
            ).fetchone()
            old_trip_id = old_trip["trip_id"] if old_trip else None

            old_time = b["depart_time"]; new_time = t["depart_time"]
            if old_time == new_time:  # idempotent
                con.execute("COMMIT")
                return {
                    "status": "ok",
                    "booking_id": bid,
                    "new_time": new_time,
                    "note": "no-op",
                    "old_trip_id": old_trip_id,
                    "new_trip_id": t["trip_id"],
                }

            fee = FEE_SAME_DAY if old_time[:10] == new_time[:10] else FEE_DIFF_DAY
            
            # Trả lại slot cho chuyến cũ (nếu có)
            if old_trip_id:
                con.execute("UPDATE trips SET seats_available = seats_available + 1 WHERE trip_id=?;", (old_trip_id,))
            
            # Trừ slot cho chuyến mới
            con.execute("UPDATE trips SET seats_available = seats_available - 1 WHERE trip_id=?;", (trip_id,))
            con.execute("UPDATE bookings SET depart_time=? WHERE booking_id=?;", (new_time, bid))
            con.execute("""INSERT INTO booking_changes(booking_id, old_time, new_time, fee)
                           VALUES (?,?,?,?);""", (bid, old_time, new_time, fee))
            con.execute("COMMIT")
            return {
                "status": "ok",
                "booking_id": bid,
                "new_time": new_time,
                "fee": fee,
                "old_trip_id": old_trip_id,
                "new_trip_id": t["trip_id"],
            }

    def cancel_booking(self, bid: str) -> Dict:
        """Hủy vé và trả lại slot cho chuyến"""
        with self._con() as con:
            con.execute("BEGIN")
            b = con.execute("SELECT * FROM bookings WHERE booking_id=?;", (bid,)).fetchone()
            if not b: 
                con.execute("ROLLBACK")
                raise KeyError("Booking not found")
            
            if b["status"] != "PAID":
                con.execute("ROLLBACK")
                return {"status": "fail", "reason": "Vé không thể hủy (chỉ hủy được vé đã thanh toán)"}
            
            # Tìm chuyến tương ứng để trả lại slot
            trip = con.execute(
                "SELECT * FROM trips WHERE route_from=? AND route_to=? AND depart_time=? LIMIT 1;",
                (b["route_from"], b["route_to"], b["depart_time"]),
            ).fetchone()
            
            if trip:
                con.execute("UPDATE trips SET seats_available = seats_available + 1 WHERE trip_id=?;", (trip["trip_id"],))
            
            con.execute("UPDATE bookings SET status='CANCELLED' WHERE booking_id=?;", (bid,))
            con.execute("COMMIT")
            
            # Tính tổng tiền đã thanh toán (giá gốc + phí đổi giờ)
            trip = con.execute(
                "SELECT * FROM trips WHERE route_from=? AND route_to=? AND depart_time=? LIMIT 1;",
                (b["route_from"], b["route_to"], b["depart_time"]),
            ).fetchone()
            
            base_price = trip["base_price"] if trip else 250_000
            
            # Tính tổng phí đổi giờ
            changes = con.execute(
                "SELECT SUM(fee) as total_fee FROM booking_changes WHERE booking_id=?;", (bid,)
            ).fetchone()
            total_change_fee = changes["total_fee"] or 0
            
            total_paid = base_price + total_change_fee
            
            return {
                "status": "ok",
                "booking_id": bid,
                "refund_amount": total_paid,  # Hoàn đúng số tiền đã thanh toán
                "base_price": base_price,
                "change_fee": total_change_fee,
                "message": "Hủy vé thành công. Tiền hoàn sẽ được chuyển về tài khoản trong 3-5 ngày làm việc."
            }

    def get_invoice(self, bid: str) -> Dict:
        """Lấy thông tin hóa đơn"""
        b = self.get_booking(bid)
        
        # Tính tổng phí đổi giờ
        with self._con() as con:
            changes = con.execute(
                "SELECT SUM(fee) as total_fee FROM booking_changes WHERE booking_id=?;", (bid,)
            ).fetchone()
            total_change_fee = changes["total_fee"] or 0
        
        # Tìm chuyến hiện tại
        trip = con.execute(
            "SELECT * FROM trips WHERE route_from=? AND route_to=? AND depart_time=? LIMIT 1;",
            (b["route_from"], b["route_to"], b["depart_time"]),
        ).fetchone()
        
        base_price = trip["base_price"] if trip else 250_000
        total_amount = base_price + total_change_fee
        
        return {
            "booking_id": bid,
            "route": f"{b['route_from']} → {b['route_to']}",
            "depart_time": b["depart_time"],
            "seat_class": b["seat_class"],
            "status": b["status"],
            "base_price": base_price,
            "change_fee": total_change_fee,
            "total_amount": total_amount,
            "invoice_date": datetime.now().isoformat()
        }

    def create_complaint(self, bid: str, complaint_type: str, description: str) -> Dict:
        """Tạo khiếu nại mới"""
        # Kiểm tra booking tồn tại
        self.get_booking(bid)
        
        with self._con() as con:
            cur = con.execute(
                """INSERT INTO complaints(booking_id, complaint_type, description) 
                   VALUES (?,?,?);""",
                (bid, complaint_type, description)
            )
            complaint_id = cur.lastrowid
            
            return {
                "complaint_id": complaint_id,
                "booking_id": bid,
                "complaint_type": complaint_type,
                "description": description,
                "status": "PENDING",
                "created_at": datetime.now().isoformat(),
                "message": "Khiếu nại đã được ghi nhận. Chúng tôi sẽ liên hệ lại trong 24h."
            }
