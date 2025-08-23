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

# Normalize and validate one command like "F700"
def normalize_command(raw: str):
    if not raw:
        return None
    s = raw.strip().upper()

    if len(s) < 2:
        return None

    direction = s[0]
    if direction not in ("F", "B", "L", "R"):
        return None

    digits = "".join(ch for ch in s[1:] if ch.isdigit())
    if digits == "":
        return None

    try:
        val = int(digits)
    except ValueError:
        return None

    if not (0 <= val <= 999):
        return None

    # Zero-pad to 3 digits; STM sees exactly 4 chars + newline
    return f"{direction}{val:03d}\n"

def main():
    # ---------- TCP setup ----------
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
                    buf = ""
                    while True:
                        chunk = conn.recv(1024)
                        if not chunk:
                            print("[TCP] Client disconnected")
                            break

                        # Accumulate and split on any whitespace/newlines
                        buf += chunk.decode(errors="ignore")
                        parts = buf.split()     # splits on any whitespace
                        # If the buffer ended without trailing whitespace,
                        # keep the last (possibly partial) token
                        buf = "" if buf.endswith(tuple([" ", "\n", "\r", "\t"])) else parts.pop() if parts else ""

                        for token in parts:
                            msg = normalize_command(token)
                            if msg is None:
                                print(f"[DROP] Invalid command: {token!r}")
                                continue

                            # Forward to UART
                            try:
                                ser.write(msg.encode("ascii"))
                                print(f"[UART] Sent: {msg.strip()}")
                            except Exception as e:
                                print(f"[UART] Write error: {e}")
                                # If UART fails, you could optionally close/reopen here

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
