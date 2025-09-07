#!/usr/bin/env python3
"""
TCP Video Client: receives frames from the Pi's USB-camera server and displays them.

Protocol (must match server):
  [4-byte big-endian length][JPEG frame bytes] repeated
"""

import argparse
import socket
import struct
import sys
import time

import cv2
import numpy as np


def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes or raise ConnectionError if the stream ends."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed while receiving")
        buf.extend(chunk)
    return bytes(buf)


def connect_with_retry(host: str, port: int, retry_delay: float = 2.0) -> socket.socket:
    """Connect to (host, port), retrying until successful or interrupted."""
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10.0)
            s.connect((host, port))
            s.settimeout(None)  # use blocking after connect
            print(f"Connected to {host}:{port}")
            return s
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"Connect failed: {e}. Retrying in {retry_delay:.1f}s...")
            time.sleep(retry_delay)


def main():
    ap = argparse.ArgumentParser(description="TCP video client for Pi USB camera server")
    ap.add_argument("--host", default="raspberrypi.local", help="Server host/IP")
    ap.add_argument("--port", type=int, default=8000, help="Server TCP port")
    ap.add_argument("--window", default="Pi Video", help="OpenCV window name")
    ap.add_argument("--show-fps", action="store_true", help="Overlay FPS on frames")
    ap.add_argument("--save", metavar="path", help="Optional: save frames (e.g., out.avi)")
    ap.add_argument("--fourcc", default="MJPG", help="FOURCC for saver (default: MJPG)")
    args = ap.parse_args()

    writer = None
    last_t = time.perf_counter()
    fps = 0.0

    while True:
        # (Re)connect
        sock = connect_with_retry(args.host, args.port)
        try:
            while True:
                # Read 4-byte length prefix (big-endian)
                header = recv_exact(sock, 4)
                (length,) = struct.unpack(">I", header)
                if length == 0:
                    continue  # skip empty frames defensively

                # Read JPEG payload
                payload = recv_exact(sock, length)

                # Decode to image
                frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    # Corrupt JPEG; skip
                    continue

                # Lazy-init VideoWriter when we see the first valid frame
                if writer is None and args.save:
                    h, w = frame.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*args.fourcc)
                    writer = cv2.VideoWriter(args.save, fourcc, 30.0, (w, h))
                    if not writer.isOpened():
                        print(f"WARNING: could not open writer to {args.save}; continuing without saving")
                        writer = None

                # FPS overlay (simple running estimate)
                if args.show_fps:
                    now = time.perf_counter()
                    dt = now - last_t
                    last_t = now
                    if dt > 0:
                        fps = 0.9 * fps + 0.1 * (1.0 / dt)  # EMA
                    cv2.putText(
                        frame, f"{fps:5.1f} FPS", (8, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA
                    )

                # Show + optional save
                cv2.imshow(args.window, frame)
                if writer is not None:
                    writer.write(frame)

                # Quit on 'q'
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    raise KeyboardInterrupt

        except KeyboardInterrupt:
            print("Exiting.")
            break
        except (ConnectionError, OSError) as e:
            print(f"Connection lost: {e}. Reconnecting…")
            # Loop will reconnect
        finally:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            sock.close()

    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
