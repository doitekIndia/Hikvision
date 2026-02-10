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

def build_rtsp(ip, username, password, channel="101"):  # Fixed channel param
    return f"rtsp://{username}:{password}@{ip}:554/ISAPI/Streaming/Channels/{channel}"

def take_screenshot(ip, username, password):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{ip}_{timestamp}.jpg".replace(".", "_")
    path = os.path.join(SCREENSHOT_DIR, filename)

    url = f"http://{ip}:8000/ISAPI/Streaming/channels/1/picture"

    try:
        r = requests.get(url, auth=HTTPDigestAuth(username, password), timeout=10)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except Exception as e:
        st.error(f"Screenshot failed for {ip}: {e}")
    return None

def rtsp_to_image(rtsp_url, timeout=15):  # Increased timeout
    """Enhanced FFmpeg with better error reporting"""
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-timeout', '5000000',  # 5s timeout
        '-i', rtsp_url,
        '-f', 'image2pipe',
        '-vframes', '1',
        '-pix_fmt', 'bgr24',
        '-'
    ]
    try:
        proc = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL
        )
        img_bytes, err = proc.communicate(timeout=timeout)
        
        if proc.returncode == 0 and img_bytes:
            return cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        else:
            st.error(f"FFmpeg failed (code {proc.returncode}): {err.decode()[:200]}")
    except subprocess.TimeoutExpired:
        proc.kill()
        st.error("FFmpeg timeout - camera unreachable")
    except Exception as e:
        st.error(f"FFmpeg error: {e}")
    return None

# ---------------- UI ----------------
st.title("🔧 Hikvision Dashboard (Enter Your Hikvision IP Camera UserName,Password and IP Address Static IP/Public IP")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

ips_raw = st.text_area(
    "Paste PUBLIC IP addresses",
    height=100,
    placeholder="136.232.171.26"
)

mode = st.radio("Mode", ["Live Frames (FFmpeg)", "Screenshot Only"])

# Fixed channel selection
channel_map = {"Main Stream (101)": "101", "Sub Stream (102)": "102"}
channel_name = st.selectbox("Stream Type", list(channel_map.keys()))
channel = channel_map[channel_name]

test_rtsp = st.checkbox("Show RTSP URL for VLC test")

submit = st.button("Start Cameras")

# ---------------- LOGIC ----------------
if submit and username and password and ips_raw:
    ips = normalize_ips(ips_raw)
    
    for ip in ips:
        with st.expander(f"📹 {ip}", expanded=True):
            rtsp_url = build_rtsp(ip, username, password, channel)
            
            if test_rtsp:
                st.code(rtsp_url)
                st.info("✅ Copy this to VLC - should work exactly like your test")
            
            if mode == "Live Frames (FFmpeg)":
                st.info("⏳ Fetching frame... (15s timeout)")
                img = rtsp_to_image(rtsp_url)
                if img is not None:
                    st.image(
                        cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
                        caption=f"✅ LIVE from {ip}",
                        use_container_width=True
                    )
                    st.success("Live frame captured!")
                else:
                    st.error("❌ No frame - check firewall/IP whitelist")
                    st.info("👉 Screenshot mode often works when live fails")
                    
                    # Try screenshot as fallback
                    st.subheader("Screenshot Fallback:")
                    image_path = take_screenshot(ip, username, password)
                    if image_path:
                        st.image(image_path, caption=f"Screenshot from {ip}", use_container_width=True)

            else:  # Screenshot mode
                image_path = take_screenshot(ip, username, password)
                if image_path:
                    st.image(image_path, caption=f"Snapshot from {ip}", use_container_width=True)
                else:
                    st.warning("Screenshot also failed - check credentials/IP")
else:
    st.info("👆 Fill all fields and click Start")


