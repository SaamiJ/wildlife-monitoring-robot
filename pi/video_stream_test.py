#!/usr/bin/env python3
"""
USB Camera TCP Streaming Server (DFRobot / UVC) for Raspberry Pi Zero 2 W

Protocol:
  [4-byte big-endian length][JPEG frame bytes] repeated

Usage (defaults to /dev/video0 @ 1280x720 15fps):
  python3 video_stream_test.py --port 8000
  # or specify device/resolution/fps/quality:
  python3 video_stream_test.py --device /dev/video0 --width 1280 --height 720 --fps 15 --quality 80
"""

import argparse
import socket
import struct
import sys
import time

import cv2


def open_usb_camera(device: str, width: int, height: int, fps: int) -> cv2.VideoCapture:
    """
    Open a UVC camera via V4L2 and request MJPEG for lower CPU on the Pi Zero 2 W.
    """
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)

    # Request MJPEG stream from the camera (much cheaper to encode/decode)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    cap.set(cv2.CAP_PROP_FPS, float(fps))

    # Give the sensor a moment and pull a couple frames to settle exposure
    warmup_deadline = time.time() + 2.0
    ok = False
    while time.time() < warmup_deadline:
        ok, _ = cap.read()
        if ok:
            break

    if not ok or not cap.isOpened():
        cap.release()
        raise RuntimeError(
            f"Failed to open camera '{device}' with requested settings {width}x{height}@{fps}fps"
        )

    # Log effective settings (camera may clamp)
    eff_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    eff_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    eff_fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
    print(
        f"Camera opened: {device}  {eff_w}x{eff_h} @{eff_fps:.1f}fps  FOURCC={fourcc_str}"
    )
    return cap


def video_streaming_server(
    host: str = "",
    port: int = 8000,
    device: str = "/dev/video0",
    width: int = 1280,
    height: int = 720,
    fps: int = 15,
    quality: int = 80,
):
    """
    Start a TCP server that streams JPEG-compressed frames from a USB UVC camera.
    The JPEG quality is configurable; 70–85 is a good Pi Zero 2 W range.
    """
    # Open camera first so we fail fast before accepting a client
    cap = open_usb_camera(device, width, height, fps)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Reuse socket quickly after restart
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Video server listening on 0.0.0.0:{port} …")

    client_socket = None
    try:
        client_socket, addr = server_socket.accept()
        print(f"Video client connected from {addr}")

        # Main streaming loop
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
        while True:
            ok, frame = cap.read()
            if not ok:
                # Try to recover a couple of times before giving up
                print("WARN: camera read failed; retrying…", file=sys.stderr)
                time.sleep(0.05)
                continue

            ok, jpeg = cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                # Skip frame if JPEG encode fails
                print("WARN: JPEG encode failed; skipping frame", file=sys.stderr)
                continue

            data = jpeg.tobytes()
            # Send 4-byte length prefix (big-endian), then the JPEG payload
            header = struct.pack(">I", len(data))
            client_socket.sendall(header + data)
            # Optional: throttle to approximate FPS if your camera outputs faster
            # time.sleep(1.0 / fps)

    except (BrokenPipeError, ConnectionResetError):
        print("Client disconnected.")
    except Exception as e:
        print(f"Video streaming error: {e}", file=sys.stderr)
    finally:
        if client_socket:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            client_socket.close()
        cap.release()
        server_socket.close()
        print("Server closed.")


def parse_args():
    p = argparse.ArgumentParser(description="USB Camera TCP Streaming Server")
    p.add_argument("--host", default="", help="Bind host (default: all interfaces)")
    p.add_argument("--port", type=int, default=8000, help="TCP port (default: 8000)")
    p.add_argument(
        "--device", default="/dev/video0", help="Video device (e.g., /dev/video0)"
    )
    p.add_argument("--width", type=int, default=1280, help="Frame width")
    p.add_argument("--height", type=int, default=720, help="Frame height")
    p.add_argument("--fps", type=int, default=15, help="Target FPS")
    p.add_argument(
        "--quality",
        type=int,
        default=80,
        help="JPEG quality (1–100, higher=better/larger)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    video_streaming_server(
        host=args.host,
        port=args.port,
        device=args.device,
        width=args.width,
        height=args.height,
        fps=args.fps,
        quality=args.quality,
    )
