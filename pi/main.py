import socket
import serial
import sys
import struct
import cv2
from picamera2 import Picamera2
import numpy as np
import threading
import RPi.GPIO as GPIO
import time
import json
import subprocess
from gpiozero import LED


# ---------- UART setup ----------
def open_serial():
    return serial.Serial(
        port='/dev/ttyS0',         # GPIO14/15 UART on Pi
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
    )


# -------- Robot Control Server --------
def robot_control_server(ser, host = '', port = 5000):
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Robot control server listening on port {port}...")

    while True:
        conn, addr = server_socket.accept()
        print(f"Robot Control client connected from {addr}")
        with conn:
            while True:
                data = conn.recv(1024).decode().strip()
                if not data:
                    print("[TCP] Client disconnected")
                    break

                # Forward raw command directly to UART
                msg = data + "\n"
                try:
                    ser.write(msg.encode("ascii"))
                    print(f"[UART] Sent: {data}")
                except Exception as e:
                    print(f"[UART] Write error: {e}")


# -------- Audio Streaming Server --------
def audio_streaming_server(host='', port=8001, device='plughw:1,0', sample_rate=16000, channels=1, sample_fmt='S16_LE', chunk_ms=20):

    # bytes per sample for S16_LE is 2
    bytes_per_sample = 2 if sample_fmt.endswith('16_LE') else 4
    chunk_bytes = int(sample_rate * channels * bytes_per_sample * (chunk_ms / 1000.0))

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Audio server listening on port {port}...")
    client_socket, addr = server_socket.accept()
    print(f"Audio client connected from {addr}")

    # Send one-line JSON header so the client knows what to expect
    header = {
        "sample_rate": sample_rate,
        "channels": channels,
        "format": sample_fmt,
        "chunk_bytes": chunk_bytes
    }
    client_socket.sendall((json.dumps(header) + "\n").encode("utf-8"))

    # Launch arecord to capture raw PCM to stdout
    # -t raw => raw stream, no WAV header
    # Use 'hw:1,0' or 'plughw:1,0' depending on your ALSA setup
    cmd = [
        "arecord",
        "-D", device,
        "-c", str(channels),
        "-r", str(sample_rate),
        "-f", sample_fmt,
        "-t", "raw"
    ]
    # Buffer size helps arecord; we’ll read exact chunk sizes
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

    try:
        while True:
            # Read exactly chunk_bytes from arecord
            chunk = proc.stdout.read(chunk_bytes)
            if not chunk or len(chunk) != chunk_bytes:
                # End or underrun; attempt a short wait then continue
                time.sleep(0.005)
                continue
            # Send length prefix + data
            client_socket.sendall(struct.pack(">I", len(chunk)) + chunk)
    except Exception as e:
        print(f"Audio streaming error: {e}")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        client_socket.close()
        server_socket.close()


# -------- Video Streaming Server (unchanged) --------
# def video_streaming_server(host='', port=8000):
#     server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     server_socket.bind((host, port))
#     server_socket.listen(1)
#     print(f"Video server listening on port {port}...")
#     client_socket, addr = server_socket.accept()
#     print(f"Video client connected from {addr}")

#     picam2 = Picamera2()
#     config = picam2.create_still_configuration(main={"size": (1280, 720)})
#     picam2.configure(config)
#     picam2.start()
#     time.sleep(2)  # camera warm-up

#     try:
#         while True:
#             frame = picam2.capture_array()
#             ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
#             if not ret:
#                 continue
#             data = jpeg.tobytes()
#             client_socket.sendall(struct.pack(">I", len(data)) + data)
#     except Exception as e:
#         print(f"Video streaming error: {e}")
#     finally:
#         picam2.stop()
#         client_socket.close()
#         server_socket.close()

# Improved Video Streaming Server with multiple clients support chat gpt
def video_streaming_server(host='', port=8000):
    import errno
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Video server listening on port {port}...")

    clients = set()
    clients_lock = threading.Lock()

    def accept_loop():
        while True:
            try:
                conn, addr = server_socket.accept()
                conn.settimeout(1.0)  # short timeout so a slow client won't stall forever
                with clients_lock:
                    clients.add(conn)
                print(f"[VIDEO] Client connected from {addr} (total: {len(clients)})")
            except Exception as e:
                print(f"[VIDEO] Accept error: {e}")

    # start acceptor thread
    threading.Thread(target=accept_loop, daemon=True).start()

    # camera init (same as yours)
    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={"size": (1280, 720)})
    picam2.configure(config)
    picam2.start()
    time.sleep(2)  # warm-up

    try:
        while True:
            frame = picam2.capture_array()
            ok, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                continue
            data = jpeg.tobytes()
            packet = struct.pack(">I", len(data)) + data  # length prefix + JPEG

            # broadcast to all clients
            dead = []
            with clients_lock:
                for c in list(clients):
                    try:
                        c.sendall(packet)
                    except (socket.timeout, BrokenPipeError, ConnectionResetError, OSError) as e:
                        # mark dead clients to remove
                        dead.append(c)
                # cleanup dead clients
                for c in dead:
                    try:
                        clients.remove(c)
                        c.close()
                    except Exception:
                        pass
                if dead:
                    print(f"[VIDEO] Dropped {len(dead)} client(s). Active: {len(clients)}")
    except Exception as e:
        print(f"Video streaming error: {e}")
    finally:
        picam2.stop()
        with clients_lock:
            for c in list(clients):
                try: c.close()
                except Exception: pass
            clients.clear()
        server_socket.close()



# -------- Main --------
if __name__ == "__main__":

    # Toggle NRST on STM32 to boot and run the firmware (GPIO4 is connected to NRST on STM32)
    led = LED(4)
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)
    led.on()
    time.sleep(0.5)

    # Open UART port
    ser = open_serial()
    print("[UART] Opened /dev/ttyS0 @115200")

    # Start servers in separate threads
    control_thread = threading.Thread(target=robot_control_server, args=(ser,), daemon=True)
    video_thread = threading.Thread(target=video_streaming_server, daemon=True)
    audio_thread = threading.Thread(
        target=audio_streaming_server,
        kwargs={"port": 8001, "device": "plughw:1,0", "sample_rate": 16000, "channels": 1, "sample_fmt": "S16_LE"},
        daemon=True
    )
    control_thread.start()
    video_thread.start()
    audio_thread.start()

    print("Pi servers running (video:8000, audio:8001, control:5000). Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SYS] Interrupted by user")
        GPIO.cleanup()
    except Exception as e:
        print(f"[SYS] Error: {e}", file=sys.stderr)
    finally:
        try:
            if ser and ser.is_open:
                ser.close()
                print("[UART] Closed")
        except Exception:
            pass