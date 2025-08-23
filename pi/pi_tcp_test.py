import socket
import serial
import sys

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

def main():
    HOST = '0.0.0.0'
    PORT = 5000

    ser = None
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
