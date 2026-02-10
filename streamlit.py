import streamlit as st
import subprocess
import os
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime
import time
import re

# ---------------- CONFIG ----------------
VLC_PATH = r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

st.set_page_config(page_title="Hikvision Dashboard", layout="centered")

# ---------------- FUNCTIONS ----------------
def normalize_ips(raw_input):
    raw_input = raw_input.replace("\r", "")
    parts = re.split(r"[,\n]+", raw_input)
    return [ip.strip() for ip in parts if ip.strip()]

def open_vlc(ip, username, password):
    rtsp_url = f"rtsp://{username}:{password}@{ip}/Streaming/Channels/101"
    return subprocess.Popen([
        VLC_PATH,
        rtsp_url,
        "--rtsp-tcp",
        "--network-caching=150"
    ])

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
    except:
        pass

    return None

# ---------------- UI ----------------
st.title("📷 Hikvision Camera Dashboard")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

ips_raw = st.text_area(
    "Paste IP addresses (one per line or comma separated)",
    height=150
)

mode = st.radio(
    "Mode",
    ["Live View in VLC", "Screenshot (Auto Close VLC)"]
)

submit = st.button("Submit")

# ---------------- LOGIC ----------------
if submit:
    if not username or not password or not ips_raw:
        st.error("Please fill all fields")
    else:
        ips = normalize_ips(ips_raw)
        results = []

        with st.spinner("Processing cameras..."):
            for ip in ips:
                st.write(f"🔹 Processing {ip}")

                if mode == "Live View in VLC":
                    open_vlc(ip, username, password)

                else:
                    vlc_process = open_vlc(ip, username, password)
                    time.sleep(2)
                    vlc_process.terminate()

                    image_path = take_screenshot(ip, username, password)
                    if image_path:
                        results.append((ip, image_path))

        # ---------------- RESULTS ----------------
        if results:
            st.subheader("📸 Screenshots")
            for ip, image_path in results:
                st.markdown(f"**Camera IP:** {ip}")
                st.image(image_path, use_container_width=True)
