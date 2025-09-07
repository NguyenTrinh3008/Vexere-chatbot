import os
import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8081/chat")

st.set_page_config(page_title="Vexere Change-Time Bot", page_icon="🚌", layout="centered")
st.title("🚌 Vexere — Đổi giờ vé (POC)")

# ----- state -----
if "api_url" not in st.session_state:
    st.session_state.api_url = DEFAULT_API_URL
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "u1"
if "messages" not in st.session_state:
    st.session_state.messages = []  # [(role, content)]

# ----- sidebar -----
with st.sidebar:
    st.header("Cấu hình")
    st.session_state.api_url = st.text_input("API URL", value=st.session_state.api_url, help="VD: http://localhost:8081/chat")
    st.session_state.thread_id = st.text_input("Thread ID", value=st.session_state.thread_id)
    if st.button("🔄 Reset hội thoại"):
        st.session_state.messages = []
        st.success("Đã reset hội thoại.")

def call_api(msg: str):
    r = requests.post(
        st.session_state.api_url,
        json={"message": msg, "thread_id": st.session_state.thread_id},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()

# ----- render lịch sử -----
for role, content in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(content)

# ----- chat input -----
if prompt := st.chat_input("Nhập tin nhắn…"):
    st.session_state.messages.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        data = call_api(prompt)
        reply = data.get("reply", "")
        with st.chat_message("assistant"):
            st.markdown(reply, unsafe_allow_html=False)
            with st.expander("🔍 Chi tiết trạng thái / kết quả"):
                st.json({
                    "intent": data.get("intent"),
                    "booking_id": data.get("booking_id"),
                    "date": data.get("date"),
                    "trip_id": data.get("trip_id"),
                    "result": data.get("result"),
                })
        st.session_state.messages.append(("assistant", reply))
    except requests.RequestException as e:
        with st.chat_message("assistant"):
            st.error(f"Lỗi gọi API: {e}\nKiểm tra API URL và uvicorn đang chạy?")

