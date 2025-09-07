# Vexere Chatbot – Setup & Run Guide

## 1) Yêu cầu
- Python 3.11+
- OpenAI API key (env `OPENAI_API_KEY`)

## 2) Cài đặt local
```bash
# 1) Tạo venv và cài dep
python -m venv .venv
. .venv/Scripts/activate  
pip install -r requirements.txt

# 2) Seed DB (tạo src/data/mock.db từ schema)
python src/data/seed.py

# 3) Chạy các service ở 3 terminal
uvicorn src.app.main:app --port 8080          # Booking API
uvicorn src.app.chat_api:app --port 8081      # Chat API
streamlit run src/ui/booking_ui.py            # UI
```

Endpoints:
- Booking API: http://localhost:8080/docs
- Chat API: http://localhost:8081/health
- UI: http://localhost:8501

Ghi chú:
- Nếu gặp lỗi import khi chạy script standalone, set `PYTHONPATH` về project root.
- RAG-FAQ sẽ đọc `src/data/faq_data.csv` và lưu embeddings vào `src/data/chroma_db/`.

## 3) Chạy bằng Docker Compose
```bash
# Set API key (PowerShell)
$env:OPENAI_API_KEY="sk-..."

# Build & run
docker compose up --build
```
- Services:
  - booking_api: 8080
  - chat_api: 8081
  - ui: 8501
- Volumes mount `./src` và `./src/data` -> bạn có thể cập nhật code/data và refresh.

## 4) Vẽ pipeline LangGraph
```bash
python src/scripts/visualize_graph.py
# Ảnh lưu tại: src/scripts/graph.png
```

## 5) Luồng kiểm thử nhanh
1) UI mở http://localhost:8501 và hỏi:
   - "Xem thông tin vé VX123456"
2) Đổi giờ:
   - "Đổi giờ vé VX123456 sang ngày 6 tháng 9"
   - Trả lời mã chuyến: `T001`
3) Hủy / hóa đơn / khiếu nại:
   - "Hủy vé VX123456"
   - "Xuất hóa đơn VX123456"
   - "Tạo khiếu nại cho VX123456 ..."
4) FAQ (RAG):
   - "Cần những giấy tờ gì khi làm thủ tục?"

## 6) Cấu trúc src/
```
src/
  app/                # FastAPI apps (booking_api, chat_api)
  orchestrator/       # LangGraph, nodes, routing, LLM extraction, RAG, media skeleton
  services/           # SQLite service
  ui/                 # Streamlit UI
  data/               # schema.sql, seed.py, mock.db, faq_data.csv, chroma_db/
  scripts/            # visualize_graph.py
  tests/              # smoke tests
```

## 7) Biến môi trường
- `OPENAI_API_KEY`: khóa để gọi LLM/embeddings.

## 8) Lưu ý
- RAG đang ở chế độ "strict" (trả lời đúng theo tài liệu retrieve được; nếu không khớp sẽ báo không có thông tin).
- Media (image/voice) đã có skeleton nodes, sẵn sàng tích hợp GPT-4o/Whisper.
