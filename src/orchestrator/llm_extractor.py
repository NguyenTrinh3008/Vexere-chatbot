"""
LLM-based information extraction module.
Handles intent classification and field extraction using OpenAI.
"""

import json
from datetime import datetime
from typing import Dict, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI configuration
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Thiếu OPENAI_API_KEY (đặt env hoặc .env).")

oai_client = OpenAI(api_key=OPENAI_API_KEY)

# Structured Output schema
EXTRACT_SCHEMA = {
    "name": "ChangeTimeFields",
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "description": "Phân loại ý định của user: change_time, check_booking, view_trips, cancel_booking, get_invoice, create_complaint, faq, unknown",
                "enum": ["change_time", "check_booking", "view_trips", "cancel_booking", "get_invoice", "create_complaint", "faq", "unknown"]
            },
            "booking_id": {
                "type": "string",
                "description": "Mã vé Vexere",
                "pattern": "^VX\\d{6,}$"
            },
            "date": {
                "type": "string",
                "description": "Ngày muốn đổi theo ISO (YYYY-MM-DD). Nếu user ghi dd/mm, hãy chuyển sang ISO và mặc định năm 2025.",
                "pattern": "^(?:19|20)\\d\\d-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\\d|3[01])$"
            },
            "trip_id": {
                "type": "string",
                "description": "Mã chuyến",
                "pattern": "^T\\d{3,}$"
            },
            "route_from": {
                "type": "string",
                "description": "Điểm đi từ câu nói (ví dụ: HCM, Hanoi, Da Lat). Tìm từ 'từ' để xác định điểm đi."
            },
            "route_to": {
                "type": "string", 
                "description": "Điểm đến từ câu nói (ví dụ: HCM, Hanoi, Da Lat). Tìm từ 'đến' để xác định điểm đến."
            },
            "complaint_type": {
                "type": "string",
                "description": "Loại khiếu nại (SERVICE, REFUND, CANCELLATION, OTHER). Nếu không phải khiếu nại thì để null.",
                "enum": ["SERVICE", "REFUND", "CANCELLATION", "OTHER"]
            },
            "description": {
                "type": "string",
                "description": "Mô tả chi tiết khiếu nại. Nếu không phải khiếu nại thì để null."
            }
        },
        "additionalProperties": False,
        "required": []
    },
    "strict": True
}

def get_enhanced_system_prompt() -> str:
    """Get the Chain of Thought system prompt for LLM extraction."""
    return (
        "Bạn là bộ trích xuất dữ liệu thông minh cho CSKH Vexere. "
        "Nhiệm vụ: Trích xuất thông tin từ câu nói của khách hàng về việc đổi giờ vé, kiểm tra vé, hoặc xem chuyến. "
        "\n"
        "QUAN TRỌNG: Bạn PHẢI trích xuất TẤT CẢ các trường có trong schema, kể cả khi chúng là null. "
        "Ví dụ: nếu user nói 'Xem chuyến từ HCM đến Da Lat', bạn phải trả về: "
        '{"intent": "view_trips", "booking_id": null, "date": null, "trip_id": null, "route_from": "HCM", "route_to": "Da Lat", "complaint_type": null, "description": null}'
        "\n"
        "\n"
        "HÃY SUY LUẬN THEO CHAIN OF THOUGHT:\n"
        "\n"
        "BƯỚC 1: PHÂN TÍCH CÂU NÓI VÀ PHÂN LOẠI INTENT\n"
        "- Đọc kỹ câu nói của khách hàng và hiểu ý định\n"
        "- Phân loại intent dựa trên ngữ cảnh và ý nghĩa:\n"
        "  * change_time: Đổi giờ vé, đổi chuyến, thay đổi lịch trình\n"
        "  * check_booking: Kiểm tra thông tin vé, xem trạng thái vé\n"
        "  * view_trips: Xem danh sách chuyến, lịch trình, tuyến đường\n"
        "  * cancel_booking: Hủy vé, không đi nữa, hủy chuyến\n"
        "  * get_invoice: Xuất hóa đơn, xem hóa đơn, tính tiền\n"
        "  * create_complaint: Khiếu nại, phản ánh, góp ý\n"
        "  * faq: Câu hỏi thường gặp, hỗ trợ, chính sách, quy định, hướng dẫn, giấy tờ, thủ tục\n"
        "  * unknown: Không xác định được ý định\n"
        "- QUAN TRỌNG: Phân tích dựa trên ý nghĩa, không chỉ từ khóa\n"
        "- QUAN TRỌNG: Nếu có 'từ X đến Y' và 'ngày' thì ưu tiên view_trips\n"
        "- QUAN TRỌNG: Câu hỏi về chính sách, quy định, hướng dẫn, giấy tờ, thủ tục → faq\n"
        "- QUAN TRỌNG: Nếu có 'sang' hoặc 'đổi' thì ưu tiên change_time\n"
        "- QUAN TRỌNG: Nếu là câu hỏi về chính sách, quy định, hướng dẫn thì ưu tiên faq\n"
        "\n"
        "BƯỚC 2: TÌM MÃ VÉ (booking_id)\n"
        "- Tìm pattern: VX + số (ví dụ: VX123456)\n"
        "- Có thể xuất hiện dưới dạng: 'vé VX123456', 'booking VX123456', 'VX123456'\n"
        "- Nếu không tìm thấy: null\n"
        "\n"
        "BƯỚC 3: TÌM NGÀY THÁNG (date)\n"
        "- Người Việt thường nói: '6 tháng 9' = ngày 6 tháng 9 = 2025-09-06\n"
        "- Các format khác:\n"
        "  * 'ngày 6 tháng 9' = 2025-09-06\n"
        "  * '6/9' = 2025-09-06 (dd/mm)\n"
        "  * '06/09' = 2025-09-06\n"
        "  * '6-9' = 2025-09-06\n"
        "  * '6/9/2025' = 2025-09-06\n"
        "  * 'ngày 6 tháng 9 năm 2025' = 2025-09-06\n"
        "- Nếu không có năm: mặc định 2025\n"
        "- Nếu không tìm thấy: null\n"
        "\n"
        "BƯỚC 4: TÌM MÃ CHUYẾN (trip_id)\n"
        "- Tìm pattern: T + số (ví dụ: T001)\n"
        "- Có thể xuất hiện dưới dạng: 'chuyến T001', 'trip T001', 'T001'\n"
        "- Nếu không tìm thấy: null\n"
        "\n"
        "BƯỚC 5: TÌM TUYẾN ĐƯỜNG (route_from, route_to)\n"
        "- Tìm điểm đi: 'HCM', 'TP.HCM', 'Sài Gòn', 'Ho Chi Minh', 'Hanoi', 'Hà Nội', 'Da Lat', 'Đà Lạt', 'Nha Trang', 'Vung Tau', 'Cần Tho'\n"
        "- Tìm điểm đến: 'HCM', 'TP.HCM', 'Sài Gòn', 'Ho Chi Minh', 'Hanoi', 'Hà Nội', 'Da Lat', 'Đà Lạt', 'Nha Trang', 'Vung Tau', 'Cần Tho'\n"
        "- Các từ khóa tuyến: 'từ HCM đến Da Lat', 'HCM - Da Lat', 'HCM đi Da Lat', 'Xem chuyến từ HCM đến Da Lat'\n"
        "- QUAN TRỌNG: Tìm từ 'từ' để xác định điểm đi, từ 'đến' để xác định điểm đến\n"
        "- Nếu không tìm thấy: null\n"
        "\n"
        "BƯỚC 6: TÌM THÔNG TIN KHIẾU NẠI (complaint_type/description)\n"
        "- Nếu có từ khóa khiếu nại, xác định loại:\n"
        "  * SERVICE: về dịch vụ, nhân viên, chất lượng\n"
        "  * REFUND: về hoàn tiền, tài chính\n"
        "  * CANCELLATION: về hủy vé, đổi vé\n"
        "  * OTHER: các vấn đề khác\n"
        "- Trích xuất mô tả chi tiết khiếu nại\n"
        "- Nếu không phải khiếu nại: null cho cả hai trường\n"
        "\n"
        "BƯỚC 7: KIỂM TRA VÀ CHUYỂN ĐỔI\n"
        "- Đảm bảo ngày tháng đúng format YYYY-MM-DD\n"
        "- Đảm bảo mã vé đúng format VX + số\n"
        "- Đảm bảo mã chuyến đúng format T + số\n"
        "- Đảm bảo tuyến đường đúng format (HCM, Da Lat, etc.)\n"
        "\n"
        "BƯỚC 8: TRẢ VỀ KẾT QUẢ\n"
        "- Chỉ trả về JSON hợp lệ theo schema\n"
        "- BAO GỒM intent đã phân loại ở BƯỚC 1\n"
        "- Nếu không tìm thấy thông tin: trả về null cho trường đó\n"
        "- Không thêm giải thích, chỉ JSON\n"
        "\n"
        "VÍ DỤ SUY LUẬN CHI TIẾT:\n"
        "\n"
        "VÍ DỤ 1:\n"
        "Input: 'Mình muốn đổi giờ vé VX123456 sang ngày 6 tháng 9'\n"
        "Bước 1: Phân tích câu nói và phân loại intent\n"
        "  - Từ khóa: 'đổi giờ', 'vé', 'sang ngày'\n"
        "  - Ngữ cảnh: đổi giờ vé ✓\n"
        "  - Intent: change_time ✓\n"
        "Bước 2: Tìm mã vé\n"
        "  - Tìm thấy: 'VX123456'\n"
        "  - Kết quả: VX123456 ✓\n"
        "Bước 3: Tìm ngày tháng\n"
        "  - Tìm thấy: '6 tháng 9'\n"
        "  - Phân tích: ngày 6, tháng 9\n"
        "  - Chuyển đổi: 2025-09-06 ✓\n"
        "Bước 4: Tìm mã chuyến\n"
        "  - Không tìm thấy\n"
        "  - Kết quả: null\n"
        "Bước 5: Kiểm tra format\n"
        "  - intent: change_time ✓\n"
        "  - booking_id: VX123456 ✓\n"
        "  - date: 2025-09-06 ✓\n"
        "  - trip_id: null ✓\n"
        "Bước 6: Kết quả cuối\n"
        "{\"intent\": \"change_time\", \"booking_id\": \"VX123456\", \"date\": \"2025-09-06\", \"trip_id\": null, \"route_from\": null, \"route_to\": null, \"complaint_type\": null, \"description\": null}\n"
        "\n"
        "VÍ DỤ 2:\n"
        "Input: 'hủy vé'\n"
        "Bước 1: Phân tích câu nói và phân loại intent\n"
        "  - Từ khóa: 'hủy vé'\n"
        "  - Ngữ cảnh: hủy vé ✓\n"
        "  - Intent: cancel_booking ✓\n"
        "Bước 2-7: Không tìm thấy thông tin khác\n"
        "Bước 8: Kết quả cuối\n"
        "{\"intent\": \"cancel_booking\", \"booking_id\": null, \"date\": null, \"trip_id\": null, \"route_from\": null, \"route_to\": null, \"complaint_type\": null, \"description\": null}\n"
        "\n"
        "VÍ DỤ 3:\n"
        "Input: 'Xem chuyến từ HCM đến Da Lat ngày 6 tháng 9'\n"
        "Bước 1: Phân tích câu nói và phân loại intent\n"
        "  - Từ khóa: 'Xem chuyến', 'từ', 'đến', 'ngày'\n"
        "  - Ngữ cảnh: xem chuyến ✓\n"
        "  - Intent: view_trips ✓\n"
        "Bước 2: Tìm mã vé\n"
        "  - Không tìm thấy\n"
        "  - Kết quả: null\n"
        "Bước 3: Tìm ngày tháng\n"
        "  - Tìm thấy: '6 tháng 9'\n"
        "  - Chuyển đổi: 2025-09-06 ✓\n"
        "Bước 4: Tìm mã chuyến\n"
        "  - Không tìm thấy\n"
        "  - Kết quả: null\n"
        "Bước 5: Tìm tuyến đường\n"
        "  - Từ: 'HCM' ✓\n"
        "  - Đến: 'Da Lat' ✓\n"
        "Bước 6: Kết quả cuối\n"
        "{\"intent\": \"view_trips\", \"booking_id\": null, \"date\": \"2025-09-06\", \"trip_id\": null, \"route_from\": \"HCM\", \"route_to\": \"Da Lat\", \"complaint_type\": null, \"description\": null}\n"
        "\n"
        "VÍ DỤ 4:\n"
        "Input: 'Làm thế nào để đặt vé máy bay?'\n"
        "Bước 1: Phân tích câu nói và phân loại intent\n"
        "  - Từ khóa: 'Làm thế nào', 'đặt vé', 'máy bay'\n"
        "  - Ngữ cảnh: câu hỏi về hướng dẫn ✓\n"
        "  - Intent: faq ✓\n"
        "Bước 2-7: Không tìm thấy thông tin khác\n"
        "Bước 8: Kết quả cuối\n"
        "{\"intent\": \"faq\", \"booking_id\": null, \"date\": null, \"trip_id\": null, \"route_from\": null, \"route_to\": null, \"complaint_type\": null, \"description\": null}\n"
        "\n"
        "VÍ DỤ 5:\n"
        "Input: 'Cần những giấy tờ gì khi làm thủ tục?'\n"
        "Bước 1: Phân tích câu nói và phân loại intent\n"
        "  - Từ khóa: 'giấy tờ', 'thủ tục', 'cần'\n"
        "  - Ngữ cảnh: câu hỏi về quy định, hướng dẫn ✓\n"
        "  - Intent: faq ✓\n"
        "Bước 2-7: Không tìm thấy thông tin khác\n"
        "Bước 8: Kết quả cuối\n"
        "{\"intent\": \"faq\", \"booking_id\": null, \"date\": null, \"trip_id\": null, \"route_from\": null, \"route_to\": null, \"complaint_type\": null, \"description\": null}\n"
        "\n"
        "KHÔNG ĐƯỢC BỎ SÓT BẤT KỲ TRƯỜNG NÀO TRONG SCHEMA!\n"
    )

def extract_fields_llm(user_text: str) -> Dict[str, Optional[str]]:
    """Extract booking_id, date, trip_id, and other fields using LLM structured output."""
    
    enhanced_system = get_enhanced_system_prompt()

    # 1) Try structured output với enhanced prompt
    try:
        resp = oai_client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_schema", "json_schema": EXTRACT_SCHEMA},
        )
        data = json.loads(resp.output_text or "{}")
        
        # Validate date format
        if "date" in data and data["date"]:
            try:
                _ = datetime.fromisoformat(data["date"])
            except Exception:
                data["date"] = None
                
        return {
            "intent": data.get("intent"),
            "booking_id": data.get("booking_id"),
            "date": data.get("date"),
            "trip_id": data.get("trip_id"),
            "route_from": data.get("route_from"),
            "route_to": data.get("route_to"),
            "complaint_type": data.get("complaint_type"),
            "description": data.get("description"),
        }
    except (TypeError, Exception):
        # Fallback nếu structured output không khả dụng
        pass

    # 2) Fallback: instruction-only với enhanced prompt
    try:
        resp = oai_client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": enhanced_system + "\n\nQUAN TRỌNG: Hãy suy luận theo 8 bước trên, sau đó chỉ trả về JSON object cuối cùng, không thêm giải thích."},
                {"role": "user", "content": user_text},
            ],
        )
        text = getattr(resp, "output_text", "") or ""
        
        # Parse JSON từ response
        try:
            data = json.loads(text)
        except Exception:
            # Tìm JSON object trong text
            import re
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    data = {}
            else:
                data = {}
        
        # Validate date format
        if "date" in data and data["date"]:
            try:
                _ = datetime.fromisoformat(data["date"])
            except Exception:
                data["date"] = None
                
        return {
            "intent": data.get("intent"),
            "booking_id": data.get("booking_id"),
            "date": data.get("date"),
            "trip_id": data.get("trip_id"),
            "route_from": data.get("route_from"),
            "route_to": data.get("route_to"),
            "complaint_type": data.get("complaint_type"),
            "description": data.get("description"),
        }
    except Exception:
        return {"intent": None, "booking_id": None, "date": None, "trip_id": None, "route_from": None, "route_to": None, "complaint_type": None, "description": None}
