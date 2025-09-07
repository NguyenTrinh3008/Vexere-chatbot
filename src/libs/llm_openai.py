# llm_openai.py
from __future__ import annotations
import os, json, re
from datetime import date as _date
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()  # tự động nạp biến từ .env

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")  
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_VN = (
    "Bạn là trợ lý CSKH của Vexere. Trả lời ngắn gọn, lịch sự bằng tiếng Việt. "
    "Nếu thiếu dữ kiện (mã vé, ngày, mã chuyến), hãy hỏi lại đúng phần thiếu."
)

def llm_reply(user_text: str, system: str = SYSTEM_VN) -> str:
    """Trả về câu trả lời tự nhiên (không cấu trúc)."""
    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
    )
    return resp.output_text  # Truy xuất text gọn của Responses API


def _normalize_two_digit_year(y: int) -> int:
    # Map 2-digit years to 2000-2099 range
    if 0 <= y <= 99:
        return 2000 + y
    return y


def _format_iso_date(day: int, month: int, year: Optional[int]) -> Optional[str]:
    try:
        today = _date.today()
        inferred_year = _normalize_two_digit_year(year) if year is not None else today.year
        candidate = _date(inferred_year, month, day)
        # If inferred date already passed this year, prefer the next year for intent-like phrasing
        if year is None and candidate < today:
            candidate = _date(inferred_year + 1, month, day)
        return candidate.strftime("%Y-%m-%d")
    except Exception:
        return None


def _heuristic_extract(user_text: str) -> Dict[str, Optional[str]]:
    text = user_text.strip()

    # booking_id like VX123456 (at least VX + 5-10 digits)
    booking_id = None
    m = re.search(r"\b(VX\d{5,12})\b", text, flags=re.IGNORECASE)
    if m:
        booking_id = m.group(1).upper()

    # trip_id like T001
    trip_id = None
    m = re.search(r"\b(T\d{2,6})\b", text, flags=re.IGNORECASE)
    if m:
        trip_id = m.group(1).upper()

    # dates like 6/9, 06/09, 6-9-2025
    iso_date = None
    # Common d/m[/y] or d-m[-y]
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", text)
    if m:
        d = int(m.group(1))
        mo = int(m.group(2))
        y = int(m.group(3)) if m.group(3) else None
        iso_date = _format_iso_date(d, mo, y)

    return {"booking_id": booking_id, "date": iso_date, "trip_id": trip_id}


def extract_fields(user_text: str) -> Dict[str, Optional[str]]:
    # First try a fast, local heuristic extractor for robustness
    heuristic = _heuristic_extract(user_text)
    if heuristic.get("booking_id") or heuristic.get("date") or heuristic.get("trip_id"):
        # If we found anything meaningful, return immediately to keep behavior deterministic
        return {
            "booking_id": heuristic.get("booking_id"),
            "date": heuristic.get("date"),
            "trip_id": heuristic.get("trip_id"),
        }

    schema = {
        "name": "ChangeTimeFields",
        "schema": {
            "type": "object",
            "properties": {
                "booking_id": {"type": "string", "description": "Mã vé, ví dụ VX123456"},
                "date":       {"type": "string", "description": "Ngày muốn đổi (YYYY-MM-DD)"},
                "trip_id":    {"type": "string", "description": "Mã chuyến gợi ý, ví dụ T001"},
            },
            "additionalProperties": False,
            "required": []
        },
        "strict": True
    }
    system_prompt = (
        "Hãy trích xuất các trường dưới dạng JSON theo schema. "
        "Nếu thiếu trường, đặt giá trị null. Chỉ trả JSON hợp lệ."
    )

    # Primary attempt: use Responses API with response_format (new SDKs)
    try:
        resp = client.responses.create(
            model=MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_schema", "json_schema": schema},
        )
        return json.loads(resp.output_text)
    except TypeError:
        # Fallback for older SDKs without response_format support
        pass
    except Exception:
        # Any other unexpected error: continue to fallback strategy
        pass

    # Fallback: coerce JSON via instruction and parse robustly
    try:
        resp = client.responses.create(
            model=MODEL,
            input=[
                {"role": "system", "content": system_prompt + " Chỉ in JSON object, không thêm giải thích."},
                {"role": "user", "content": (
                    user_text
                    + "\n\nYêu cầu: Trả về JSON với các khóa booking_id, date (YYYY-MM-DD), trip_id."
                )},
            ],
        )
        text = resp.output_text or ""
        # Try direct JSON load
        try:
            return json.loads(text)
        except Exception:
            # Extract first JSON object with regex as last resort
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
    except Exception:
        pass

    return {"booking_id": None, "date": None, "trip_id": None}
