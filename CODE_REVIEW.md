# CODE REVIEW – Self-Check

## 1) Quy ước code style
- Nguyên tắc chung
  - Ưu tiên rõ ràng, nhất quán, dễ đọc; tránh tối ưu hóa sớm.
  - Đặt tên mô tả ý nghĩa: biến là danh từ/cụm danh từ; hàm là động từ/cụm động từ.
  - Dùng guard clause, xử lý lỗi sớm; hạn chế lồng khối > 2–3 tầng.
  - Không bắt lỗi trống; mỗi except có thông điệp/handling rõ ràng.
  - Không reformat code ngoài phạm vi chỉnh sửa.
- Python
  - Type hints cho API công khai và nơi tăng rõ ràng.
  - Tránh biến 1–2 ký tự; hạn chế ép kiểu không an toàn.
  - Module hóa: `orchestrator/` (types, nodes, routing, graph, media, rag_faq), `services/`, `app/`.
  - Prompt/LLM logic tách ở `llm_extractor.py`.
- Chuỗi & ngày tháng
  - Ngày chuẩn ISO `YYYY-MM-DD` trong state và API.
  - Hàm trình bày Việt hóa ở `utils.py` (`fmt_dt_vn`, `fmt_fee_vnd`).
- Logging/Debug
  - `DEBUG:` prints ở các node chính (classify/extract) để theo dõi pipeline.
  - Không log PII thô; che mờ (mask) trước khi ghi log nếu cần.

## 2) Kiểm thử & CI
- Kiểm thử thủ công nhanh
  - API: `uvicorn src.app.main:app --port 8080` và `uvicorn src.app.chat_api:app --port 8081`.
  - UI: `streamlit run src/ui/booking_ui.py`.
  - Vẽ pipeline: `python -m src.scripts.visualize_graph`.
  - Seed DB: `python src/data/seed.py`.
- Kiểm thử hành vi (đề xuất)
  - Smoke tests cho các endpoints chính: bookings/trips/cancel/invoice/complaints.
  - Test stateful flow LangGraph: intent → route → node output.
  - Test RAG: truy vấn phủ nhiều chủ đề (hành lý, hoàn tiền, check-in…).
  - Test dữ liệu: seat counting khi đổi chuyến, hủy vé trả ghế, tính phí.
- CI
  - Trạng thái: Chưa hỗ trợ (pending).
  - Gợi ý tương lai: GitHub Actions với các job lint (`ruff`/`flake8` + `mypy`), test (`pytest -q`), và security (`pip-audit`/`safety`).

## 3) Điểm còn hạn chế & hướng mở rộng
- Hạn chế
  - Media nodes (image/audio) là skeleton, chưa tích hợp GPT-4o/Whisper thực tế.
  - Nodes gọi HTTP sync (`requests`); chưa có retry/circuit breaker.
  - Chưa có test E2E đầy đủ cho tất cả intent/nhánh đồ thị.
  - Phụ thuộc LLM cho extract/intent; khi model thay đổi có thể cần tinh chỉnh prompt.
  - Chưa có auth/rate-limit; nguy cơ lạm dụng API.
- Hướng mở rộng
  - Media
    - Tích hợp GPT-4o Vision (ảnh) và Whisper/gpt-4o-mini-transcribe (audio).
    - Chuẩn hóa ảnh (resize/compress), giới hạn kích thước, TTL cho file tạm.
  - RAG
    - Mở rộng dữ liệu FAQ; build embeddings định kỳ; cân nhắc `text-embedding-3-large` + re-ranking.
  - Kiến trúc & hiệu năng
    - Chuyển sang async I/O (`httpx`, FastAPI async), thêm caching và batching.
    - Observability: metrics, tracing, structured logs.
  - Độ tin cậy
    - Retry/idempotency cho đổi/hủy; validation chặt chẽ bằng Pydantic.
  - Trải nghiệm người dùng
    - Clarification khi thiếu trường; i18n; xử lý biến thể ngôn ngữ vùng miền.
  - Bảo mật & tuân thủ
    - Mask PII trong logs; chính sách lưu trữ dữ liệu; CORS; rate limit.

---
Tài liệu là checklist sống: cập nhật khi thay đổi kiến trúc, thêm tính năng, hoặc phát hiện nợ kỹ thuật mới.
