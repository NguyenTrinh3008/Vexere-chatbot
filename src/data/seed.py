import sqlite3, os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB = (BASE_DIR / "mock.db").as_posix()
SCHEMA = (BASE_DIR / "schema.sql").as_posix()

if os.path.exists(DB):
    os.remove(DB)

with sqlite3.connect(DB) as con, open(SCHEMA, "r", encoding="utf-8") as f:
    con.executescript(f.read())
    con.row_factory = sqlite3.Row

    # Thêm nhiều vé booking
    bookings = [
      ("VX123456","HCM","Da Lat","2025-09-05T20:00:00","PAID","Standard","+8490xxxxxxx"),
      ("VX789012","HCM","Hanoi","2025-09-07T08:00:00","PAID","Premium","+8491xxxxxxx"),
      ("VX345678","Da Lat","HCM","2025-09-06T14:00:00","PAID","Standard","+8492xxxxxxx"),
      ("VX901234","HCM","Nha Trang","2025-09-08T10:00:00","CANCELLED","Standard","+8493xxxxxxx"),
      ("VX567890","Hanoi","HCM","2025-09-09T16:00:00","PAID","Premium","+8494xxxxxxx"),
    ]
    con.executemany("""INSERT INTO bookings
      (booking_id, route_from, route_to, depart_time, status, seat_class, user_phone)
      VALUES (?,?,?,?,?,?,?)""", bookings)

    # Thêm nhiều chuyến xe cho các tuyến khác nhau
    trips = [
      # Tuyến HCM - Da Lat
      ("T001","HCM","Da Lat","2025-09-06T08:00:00",40,5,250000),
      ("T002","HCM","Da Lat","2025-09-06T14:00:00",40,2,250000),
      ("T003","HCM","Da Lat","2025-09-05T20:00:00",40,1,250000),  # chuyến hiện tại của VX123456
      ("T004","HCM","Da Lat","2025-09-05T22:00:00",40,0,250000),  # hết chỗ
      ("T005","HCM","Da Lat","2025-09-07T06:00:00",40,8,250000),
      ("T006","HCM","Da Lat","2025-09-07T12:00:00",40,3,250000),
      ("T007","HCM","Da Lat","2025-09-07T18:00:00",40,0,250000),  # hết chỗ
      
      # Tuyến HCM - Hanoi
      ("T101","HCM","Hanoi","2025-09-07T08:00:00",50,2,450000),  # chuyến hiện tại của VX789012
      ("T102","HCM","Hanoi","2025-09-07T14:00:00",50,5,450000),
      ("T103","HCM","Hanoi","2025-09-07T20:00:00",50,0,450000),  # hết chỗ
      ("T104","HCM","Hanoi","2025-09-08T08:00:00",50,7,450000),
      ("T105","HCM","Hanoi","2025-09-08T14:00:00",50,3,450000),
      
      # Tuyến Da Lat - HCM
      ("T201","Da Lat","HCM","2025-09-06T14:00:00",40,1,250000),  # chuyến hiện tại của VX345678
      ("T202","Da Lat","HCM","2025-09-06T20:00:00",40,4,250000),
      ("T203","Da Lat","HCM","2025-09-07T08:00:00",40,6,250000),
      ("T204","Da Lat","HCM","2025-09-07T14:00:00",40,0,250000),  # hết chỗ
      ("T205","Da Lat","HCM","2025-09-08T08:00:00",40,9,250000),
      
      # Tuyến HCM - Nha Trang
      ("T301","HCM","Nha Trang","2025-09-08T10:00:00",35,0,200000),  # hết chỗ (VX901234 đã cancel)
      ("T302","HCM","Nha Trang","2025-09-08T16:00:00",35,5,200000),
      ("T303","HCM","Nha Trang","2025-09-09T08:00:00",35,8,200000),
      ("T304","HCM","Nha Trang","2025-09-09T14:00:00",35,2,200000),
      
      # Tuyến Hanoi - HCM
      ("T401","Hanoi","HCM","2025-09-09T16:00:00",50,1,450000),  # chuyến hiện tại của VX567890
      ("T402","Hanoi","HCM","2025-09-09T22:00:00",50,3,450000),
      ("T403","Hanoi","HCM","2025-09-10T08:00:00",50,6,450000),
      ("T404","Hanoi","HCM","2025-09-10T14:00:00",50,4,450000),
      
      # Tuyến HCM - Vung Tau (ngắn)
      ("T501","HCM","Vung Tau","2025-09-06T07:00:00",30,12,150000),
      ("T502","HCM","Vung Tau","2025-09-06T13:00:00",30,8,150000),
      ("T503","HCM","Vung Tau","2025-09-06T19:00:00",30,15,150000),
      ("T504","HCM","Vung Tau","2025-09-07T07:00:00",30,10,150000),
      
      # Tuyến HCM - Can Tho
      ("T601","HCM","Can Tho","2025-09-06T09:00:00",45,6,180000),
      ("T602","HCM","Can Tho","2025-09-06T15:00:00",45,4,180000),
      ("T603","HCM","Can Tho","2025-09-06T21:00:00",45,0,180000),  # hết chỗ
      ("T604","HCM","Can Tho","2025-09-07T09:00:00",45,11,180000),
    ]
    con.executemany("""INSERT INTO trips
      (trip_id, route_from, route_to, depart_time, seats_total, seats_available, base_price)
      VALUES (?,?,?,?,?,?,?)""", trips)

print("Seeded mock.db")
