import streamlit as st
import cv2
import av
import os
import re
import requests
from datetime import datetime
from requests.auth import HTTPDigestAuth
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Hikvision Dashboard", layout="centered")

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ---------------- FUNCTIONS ----------------
def normalize_ips(raw_input):
    raw_input = raw_input.replace("\r", "")
    parts = re.split(r"[,\n]+", raw_input)
    return [ip.strip() for ip in parts if ip.strip()]

def build_rtsp(ip, username, password):
    # ✅ Hikvision ISAPI + substream + TCP-friendly
    return (
        f"rtsp://{username}:{password}@{ip}:554/"
        f"ISAPI/Streaming/Channels/102"
    )

def take_screenshot(ip, username, password):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{ip}_{timestamp}.jpg".replace(".", "_")
    path = os.path.join(SCREENSHOT_DIR, filename)

    url = f"http://{ip}/ISAPI/Streaming/channels/1/picture"

    try:
        r = requests.get(
            url,
            auth=HTTPDigestAuth(username, password),
            timeout=5
        )
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except Exception as e:
        st.error(f"Screenshot failed for {ip}: {e}")

    return None

# ---------------- WEBRTC PROCESSOR ----------------
class HikvisionProcessor(VideoProcessorBase):
    def __init__(self, rtsp_url):
        self.cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

        if not self.cap.isOpened():
            st.error("❌ Failed to open RTSP stream")

    def recv(self, frame):
        ret, img = self.cap.read()
        if not ret:
            return frame

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return av.VideoFrame.from_ndarray(img, format="rgb24")

# ---------------- UI ----------------
st.title("📷 Hikvision Camera Dashboard (Cloud + WebRTC)")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

ips_raw = st.text_area(
    "Paste PUBLIC IP addresses (one per line or comma separated)",
    height=150,
    placeholder="136.232.171.26\n136.232.171.27"
)

mode = st.radio(
    "Mode",
    ["Live View (WebRTC)", "Screenshot Only"]
)

submit = st.button("Submit")

# ---------------- LOGIC ----------------
if submit:
    if not username or not password or not ips_raw:
        st.error("Please fill all fields")
    else:
        ips = normalize_ips(ips_raw)

        for ip in ips:
            st.markdown(f"### 📡 Camera: `{ip}`")

            rtsp_url = build_rtsp(ip, username, password)
            st.code(rtsp_url)  # helps debugging

            if mode == "Live View (WebRTC)":
                webrtc_streamer(
                    key=f"cam-{ip}",
                    video_processor_factory=lambda: HikvisionProcessor(rtsp_url),
                    media_stream_constraints={"video": True, "audio": False},
                    rtc_configuration={
                        "iceServers": [
                            {"urls": ["stun:stun.l.google.com:19302"]}
                        ]
                    },
                )

            else:
                image_path = take_screenshot(ip, username, password)
                if image_path:
                    st.image(
                        image_path,
                        caption=f"Snapshot from {ip}",
                        use_container_width=True
                    )
                else:
                    st.warning("No snapshot received")
