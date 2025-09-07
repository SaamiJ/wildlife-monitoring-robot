#!/usr/bin/env python3
# Low-latency USB UVC camera streamer for Pi Zero 2 W
# Protocol: [4-byte big-endian length][JPEG bytes] repeated.

import argparse
import socket
import struct
import sys
import threading
import time
from queue import Queue, Full, Empty

import cv2

def open_usb_camera(device: str, width: int, height: int, fps: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    cap.set(cv2.CAP_PROP_FPS, float(fps))

    t0 = time.time()
    ok = False
    while time.time() - t0 < 2.0:
        ok, _ = cap.read()
        if ok:
            break
    if not ok or not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Failed to open {device} at {width}x{height}@{fps}")

    eff_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    eff_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    eff_fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_str = "".join([chr((fourcc >> (8*i)) & 0xFF) for i in range(4)])
    print(f"Camera: {device}  {eff_w}x{eff_h} @{eff_fps:.1f}  FOURCC={fourcc_str}")
    return cap

def producer(cap: cv2.VideoCapture, q: Queue, jpeg_quality: int, target_fps: float):
    enc_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
    frame_interval = 1.0 / max(1.0, target_fps)
    next_deadline = time.perf_counter()

    while True:
        ok, frame = cap.read()
        if not ok:
            # brief pause, then continue
            time.sleep(0.01)
            continue

        ok, jpeg = cv2.imencode(".jpg", frame, enc_params)
        if not ok:
            continue
        payload = jpeg.tobytes()

        # Latest-only queue: replace any existing item
        try:
            # if queue already has an item, remove it to keep only the newest
            try:
                q.get_nowait()
            except Empty:
                pass
            q.put_nowait(payload)
        except Full:
            # shouldn't happen with manual drain above, but ignore if it does
            pass

        # simple pacing to avoid overproducing
        next_deadline += frame_interval
        sleep_time = next_deadline - time.perf_counter()
        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            # we're late; realign to now so we don't drift
            next_deadline = time.perf_counter()

def send_all(sock: socket.socket, buf: memoryview, timeout_s: float = 0.25) -> bool:
    """Attempt to send the whole buffer within timeout; return False to drop if too slow."""
    end = time.perf_counter() + timeout_s
    sent = 0
    while sent < len(buf):
        remaining = len(buf) - sent
        # short sends to avoid monopolizing if the peer is slow
        n = sock.send(buf[sent: sent + min(remaining, 64 * 1024)])
        if n <= 0:
            return False
        sent += n
        if time.perf_counter() > end:
            return False
    return True

def streamer(host: str, port: int, device: str, width: int, height: int, fps: int, quality: int):
    cap = open_usb_camera(device, width, height, fps)

    q: Queue[bytes] = Queue(maxsize=1)  # latest-only buffer
    prod = threading.Thread(target=producer, args=(cap, q, quality, fps), daemon=True)
    prod.start()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    print(f"Listening on 0.0.0.0:{port}")

    try:
        while True:
            client, addr = srv.accept()
            print(f"Client connected: {addr}")
            # Low-latency TCP knobs
            try:
                client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                client.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 128 * 1024)
            except Exception:
                pass

            try:
                while True:
                    # get the *latest* payload, waiting briefly if needed
                    try:
                        payload = q.get(timeout=1.0)
                    except Empty:
                        continue

                    header = struct.pack(">I", len(payload))
                    # Try sending quickly; if slow, drop this frame and move on
                    if not send_all(client, memoryview(header)) or not send_all(client, memoryview(payload)):
                        print("Send slow or failed; dropping frame")
                        # If it keeps failing, ConnectionReset will break us out shortly
            except (ConnectionResetError, BrokenPipeError, OSError):
                print("Client disconnected.")
                try:
                    client.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                client.close()
            except KeyboardInterrupt:
                raise
    except KeyboardInterrupt:
        print("Shutting down…")
    finally:
        cap.release()
        srv.close()

def parse_args():
    ap = argparse.ArgumentParser(description="Low-latency USB camera streamer")
    ap.add_argument("--host", default="", help="Bind host (default: all)")
    ap.add_argument("--port", type=int, default=8000, help="TCP port")
    ap.add_argument("--device", default="/dev/video0", help="UVC device path")
    ap.add_argument("--width", type=int, default=960, help="Frame width (try 960)")
    ap.add_argument("--height", type=int, default=540, help="Frame height (try 540)")
    ap.add_argument("--fps", type=int, default=15, help="Target FPS (15 is good on Pi Zero 2 W)")
    ap.add_argument("--quality", type=int, default=72, help="JPEG quality (lower = smaller/faster)")
    return ap.parse_args()

if __name__ == "__main__":
    a = parse_args()
    streamer(a.host, a.port, a.device, a.width, a.height, a.fps, a.quality)
