from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import psutil
import socket

# -------------------------
# Detect primary Wi-Fi/Ethernet IP
# -------------------------
def get_primary_ip():
    addrs = psutil.net_if_addrs()
    for iface, iface_addrs in addrs.items():
        if iface.lower().startswith(("ras", "ppp", "vpn", "loopback", "virtual")):
            continue
        for addr in iface_addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
                if not ip.startswith("127.") and not ip.startswith("169.254."):
                    return ip
    return "127.0.0.1"

PRIMARY_IP = get_primary_ip()
print("Using primary network interface IP:", PRIMARY_IP)

# -------------------------
# yt-dlp options
# -------------------------
YDL_OPTS = {
    "quiet": True,
    "skip_download": True,
    "nocheckcertificate": True,
    "jsruntimes": ["wscript"],  # use wscript for extraction
    "source_address": PRIMARY_IP
}

# -------------------------
# Video/audio extraction
# -------------------------
def extract_formats(video_id: str):
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as e:
        return {"error": str(e)}

    formats = info.get("formats", [])
    videos = []
    audios = []

    for f in formats:
        # Video: H.264 only, up to 1080p60
        if f.get("vcodec", "").startswith("avc"):
            if f.get("height", 0) <= 1080 and f.get("fps", 0) <= 60:
                videos.append(f)

        # Audio: AAC only
        if f.get("acodec", "").startswith("mp4a"):
            audios.append(f)

    if not videos or not audios:
        return {"error": "No supported video or audio formats found."}

    # Sort best first
    videos.sort(key=lambda f: (f.get("height", 0), f.get("fps", 0), f.get("tbr", 0)), reverse=True)
    audios.sort(key=lambda f: f.get("abr", 0), reverse=True)

    # Build qualities
    qualities = [{
        "itag": v["format_id"],
        "label": f'{v.get("height")}p{int(v.get("fps", 30))}',
        "progressive": v.get("acodec") != "none",
        "url": v["url"],
        "vcodec": v.get("vcodec")
    } for v in videos]

    # Audio modes: original + "stable volume" (lowest bitrate AAC)
    original_audio = audios[0]
    stable_audio = sorted(audios, key=lambda f: f.get("abr", 0))[0]

    return {
        "title": info.get("title", "Unknown Title"),
        "qualities": qualities,
        "audio": {
            "original": original_audio["url"],
            "stable": stable_audio["url"],
        }
    }

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI()

@app.get("/api/watch")
def watch(v: str):
    data = extract_formats(v)
    if "error" in data:
        return JSONResponse(content=data, status_code=400)
    return data

@app.get("/watch")
def serve_watch():
    return FileResponse("watch.html")


