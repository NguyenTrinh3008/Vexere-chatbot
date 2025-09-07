import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.booking_sqlite import BookingServiceSQL
from datetime import datetime

svc = BookingServiceSQL("mock.db")

print("Booking:", svc.get_booking("VX123456"))
print("Candidates:", svc.get_candidates("VX123456", "2025-09-06"))
print("Quote:", svc.quote_change("VX123456", datetime.fromisoformat("2025-09-06T08:00:00")))
print("Apply:", svc.apply_change("VX123456", "T001"))
