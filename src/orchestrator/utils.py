"""
Utility functions for formatting and display.
"""

from datetime import datetime
from typing import Optional, Any

def fmt_dt_vn(iso_str_or_dt: Any) -> str:
    """Format datetime to Vietnamese format (dd/mm/yyyy HH:MM)."""
    dt = iso_str_or_dt if isinstance(iso_str_or_dt, datetime) else datetime.fromisoformat(str(iso_str_or_dt))
    return dt.strftime("%d/%m/%Y %H:%M")

def fmt_date_vn_just_day(iso_date: str) -> str:
    """Format date to Vietnamese format (dd/mm/yyyy)."""
    dt = datetime.fromisoformat(iso_date + "T00:00:00")
    return dt.strftime("%d/%m/%Y")

def fmt_fee_vnd(n: Optional[int]) -> str:
    """Format number to Vietnamese currency format."""
    return ("0 ₫" if n is None else f"{n:,.0f}".replace(",", ".") + " ₫")

def md_candidates_table(cands: list[dict]) -> str:
    """Create markdown table for trip candidates."""
    rows = ["| Mã chuyến | Giờ xuất phát | Chỗ còn |",
            "|---|---:|---:|"]
    for c in cands:
        rows.append(f"| `{c['trip_id']}` | {fmt_dt_vn(c['depart_time'])} | {c['seats_available']} |")
    return "\n".join(rows)
