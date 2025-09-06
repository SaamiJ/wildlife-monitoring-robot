import socket
import struct
import cv2
from picamera2 import Picamera2
import numpy as np
import threading
import RPi.GPIO as GPIO
import time
import serial
import sys
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

# --- Video Streaming Server ---
def video_streaming_server(host='', port=8000):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Video server listening on port {port}...")
    client_socket, addr = server_socket.accept()
    print(f"Video client connected from {addr}")

    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={"size": (1280, 720)})
    picam2.configure(config)
    picam2.start()
    time.sleep(2)  # camera warm-up

    try:
        while True:
            frame = picam2.capture_array()
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                continue

            data = jpeg.tobytes()
            client_socket.sendall(struct.pack(">I", len(data)) + data)
            print(f"Sent frame of size {len(data)} bytes")
    except Exception as e:
        print(f"Video streaming error: {e}")
    finally:
        picam2.stop()
        client_socket.close()
        server_socket.close()

def main():
    HOST = '0.0.0.0'
    PORT = 5000

    ser = None

    # Toggle NRST on STM32 to boot and run the code
    led = LED(4)
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)
    led.on()
    time.sleep(0.5)

    video_thread = threading.Thread(target=video_streaming_server, daemon=True)

    video_thread.start()

    print("Pi servers running. Press Ctrl+C to exit.")

    try:
        ser = open_serial()
        print("[UART] Opened /dev/ttyS0 @115200")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((HOST, PORT))
            srv.listen(1)
            print(f"[TCP] Listening on {HOST}:{PORT}")

            while True:
                conn, addr = srv.accept()
                print(f"[TCP] Connected by {addr}")
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

if __name__ == "__main__":
    main()