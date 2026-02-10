import streamlit as st
import cv2
import subprocess
import numpy as np
import os
import re
import requests
from datetime import datetime
from requests.auth import HTTPDigestAuth
import time

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Hikvision Dashboard", layout="centered")

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ---------------- FUNCTIONS ----------------
def normalize_ips(raw_input):
    raw_input = raw_input.replace("\\r", "")
    parts = re.split(r"[,\\n]+", raw_input)
    return [ip.strip() for ip in parts if ip.strip()]

def build_rtsp(ip, username, password, channel="101"):  # Default to main stream
    return f"rtsp://{username}:{password}@{ip}:554/ISAPI/Streaming/Channels/{channel}"

def take_screenshot(ip, username, password):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{ip}_{timestamp}.jpg".replace(".", "_")
    path = os.path.join(SCREENSHOT_DIR, filename)

    url = f"http://{ip}:8000/ISAPI/Streaming/channels/1/picture"

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

def rtsp_to_image(rtsp_url, timeout=10):
    """FFmpeg RTSP → single frame (cloud-compatible)"""
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-f', 'image2pipe',
        '-vframes', '1',
        '-pix_fmt', 'bgr24',
        '-'
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        img_bytes, err = proc.communicate(timeout=timeout)
        if proc.returncode == 0 and img_bytes:
            return cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    except subprocess.TimeoutExpired:
        proc.kill()
    except Exception as e:
        st.error(f"FFmpeg error: {e}")
    return None

# ---------------- UI ----------------
st.title("📷 Hikvision Dashboard (Cloud-Friendly)")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

ips_raw = st.text_area(
    "Paste PUBLIC IP addresses (one per line or comma separated)",
    height=150,
    placeholder="136.232.171.26\n10.20.10.22"
)

mode = st.radio(
    "Mode",
    ["Live Frames (FFmpeg - Cloud OK)", "Screenshot Only"]
)

channel = st.selectbox("Stream", ["101 (Main/High Res)", "102 (Sub/Low Latency)"])

refresh_rate = st.slider("Refresh (seconds)", 1, 10, 3)

submit = st.button("Start")

# ---------------- LOGIC ----------------
if submit and username and password and ips_raw:
    ips = normalize_ips(ips_raw)
    
    for ip in ips:
        with st.expander(f"📡 Camera: `{ip}`", expanded=True):
            rtsp_url = build_rtsp(ip, username, password, channel[-3:])  # Extract 101/102
            st.code(rtsp_url)

            if mode == "Live Frames (FFmpeg - Cloud OK)":
                placeholder = st.empty()
                
                # Continuous live refresh
                while True:
                    with placeholder.container():
                        img = rtsp_to_image(rtsp_url)
                        if img is not None:
                            st.image(
                                cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
                                caption=f"Live from {ip} (refreshes every {refresh_rate}s)",
                                use_container_width=True
                            )
                        else:
                            st.warning(f"Failed to fetch frame from {ip}")
                    
                    time.sleep(refresh_rate)
                    st.rerun()  # Refresh page for new frame

            else:  # Screenshot
                image_path = take_screenshot(ip, username, password)
                if image_path:
                    st.image(
                        image_path,
                        caption=f"Snapshot from {ip}",
                        use_container_width=True
                    )
                else:
                    st.warning("No snapshot received")
else:
    st.info("👆 Enter credentials and IPs, then click Submit")
