import ctypes
import hashlib
import json
import os
import socket
import subprocess
import time
import urllib.request
from ctypes import wintypes

QR = r"<AiQQ>\NapCat\napcat\cache\qrcode.png"
LOGIN_URL = "http://127.0.0.1:3000/get_login_info"
LOCK_PORT = 8099
HOST = "127.0.0.1"
OPEN_COOLDOWN_SEC = 30

user32 = ctypes.windll.user32


def acquire_lock():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((HOST, LOCK_PORT))
        s.listen(1)
        return s
    except OSError:
        return None


def logged_in():
    try:
        req = urllib.request.Request(LOGIN_URL, timeout=4)
        with urllib.request.urlopen(req, timeout=4) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        return d.get("retcode") == 0 and bool((d.get("data") or {}).get("user_id"))
    except Exception:
        return False


def qr_hash():
    try:
        with open(QR, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None


def close_qr_windows():
    """Close open image viewer windows showing qrcode.png."""
    closed = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            if "qrcode" in title.lower():
                user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                closed.append(title)
        return True

    user32.EnumWindows(cb, 0)
    return closed


def open_qr(path):
    try:
        os.startfile(path)
    except Exception:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", path], shell=False)
        except Exception:
            pass


def main():
    lock = acquire_lock()
    if lock is None:
        return
    last_hash = None
    last_open_ts = 0.0
    while True:
        try:
            online = logged_in()
            if online:
                last_hash = None
            elif os.path.exists(QR):
                h = qr_hash()
                now = time.time()
                if h and h != last_hash and now - last_open_ts > OPEN_COOLDOWN_SEC:
                    last_hash = h
                    last_open_ts = now
                    close_qr_windows()
                    time.sleep(0.8)
                    open_qr(QR)
        except Exception:
            pass
        time.sleep(6)


if __name__ == "__main__":
    main()
