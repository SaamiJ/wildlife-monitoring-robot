# Import libraries
import sys, time
import serial

PORT = "/dev/ttyS0"   # Pi’s primary UART alias
BAUD = 115200           # Match STM32 
TIMEOUT_S = 0.2         

# Opens an 8N1 UART port
def open_port():
    ser = serial.Serial(
        PORT, BAUD,
        timeout=TIMEOUT_S,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        xonxoff=False, rtscts=False, dsrdtr=False,
        write_timeout=0.5,
    )
    time.sleep(0.1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    return ser

# Converts line to ASCII and writes to UART 
def send_line(ser, line: str):
    ser.write((line.strip() + "\n").encode("ascii"))
    ser.flush()

# Reads and decodes line from ASCII to python
def read_lines_nonblock(ser):
    out = []
    while True:
        line = ser.readline()
        if not line:
            break
        out.append(line.decode("ascii", errors="replace").rstrip())
    return out


def main():
    print(f"Opening {PORT} @ {BAUD}…")
    try:
        # Open serial port
        ser = open_port()
    except Exception as e:
        print(f"Failed to open port: {e}")
        sys.exit(1)

    # User menu
    print("Commands:")
    print("  pwm <0-1000>   -> set duty (%)")
    print("  stop          -> stop PWM (0%)")
    print("  raw <text>    -> send raw line")
    print("  quit          -> exit\n")

    try:
        while True:
            # poll for messages from STM32
            for resp in read_lines_nonblock(ser):
                print(f"[STM32] {resp}")

            # Prompts user for command interrupt
            try:
                cmd = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            # Type quit or exit to leave loop
            if not cmd:
                continue
            if cmd.lower() in ("quit", "exit"):
                break

            # If pwm input, clamp and send integer 0-1000
            if cmd.lower().startswith("pwm "):
                try:
                    pct = int(cmd.split()[1])
                    pct = max(0, min(1000, pct))
                    send_line(ser, f"PWM {pct}")
                except (IndexError, ValueError):
                    print("Usage: pwm <0-1000>")
            
            # If stop input, set PWM to 0
            elif cmd.lower() == "stop":
                send_line(ser, "PWM 0")
            # Freeform command 
            elif cmd.lower().startswith("raw "):
                send_line(ser, cmd[4:])
            else:
                print("Unknown: pwm <0-1000>, stop, raw <text>, quit")

            for resp in read_lines_nonblock(ser):
                print(f"[STM32] {resp}")
    finally:
        ser.close()
        print("Closed.")

if __name__ == "__main__":
    main()
