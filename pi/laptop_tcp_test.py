import socket
import keyboard
import time

# Define the Pi Zero's IP address and port
HOST = '172.20.10.5'
PORT = 5000

# Create socket connection to Pi
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

print("Connected to Pi Zero 2. Hold WASD for direction. +/- to change speed. 'q' to quit.")

speed = 500  # Initial speed 0–999
prev_dir = None       # 'F','B','L','R', or None (idle)
last_sent = None      # cache last full command string (e.g., 'F500')

def speed_str(val: int) -> str:
    # zero-pad to 3 digits
    return f"{max(0, min(999, val)):03d}"

def current_direction():
    # Priority order if multiple keys are pressed at once (customize if desired)
    if keyboard.is_pressed('w'): return 'F'
    if keyboard.is_pressed('s'): return 'B'
    if keyboard.is_pressed('a'): return 'L'
    if keyboard.is_pressed('d'): return 'R'
    return None

try:
    while True:
        # Handle quit
        if keyboard.is_pressed('q'):
            sock.sendall(b'STOP\n')
            break

        # Handle speed updates
        changed_speed = False
        if keyboard.is_pressed('+') and speed < 999:
            old = speed
            speed = min(999, speed + 50)
            if speed != old:
                print(f"Speed increased to {speed}")
                changed_speed = True

        if keyboard.is_pressed('-') and speed > 0:
            old = speed
            speed = max(0, speed - 50)
            if speed != old:
                print(f"Speed decreased to {speed}")
                changed_speed = True

        # drain +/− while held so it doesn't keep repeating in the OS buffer
        while keyboard.is_pressed('+') or keyboard.is_pressed('-'):
            time.sleep(0.01)

        # Determine current direction based on pressed keys
        cur_dir = current_direction()

        # If a direction key is held: send that command (only on change or speed change)
        if cur_dir is not None:
            cmd = f"{cur_dir}{speed_str(speed)}"
            if cmd != last_sent:
                sock.sendall((cmd + "\n").encode())
                last_sent = cmd
                prev_dir = cur_dir

        # If no direction key is held and we were previously moving: send stop once
        else:
            if prev_dir is not None or (last_sent and not last_sent.endswith("000")):
                sock.sendall(b"F000\n")   # unified stop (0 PWM)
                last_sent = "F000"
                prev_dir = None

        time.sleep(0.01)  # light polling delay to reduce CPU

finally:
    sock.close()
