import serial
import time

# Configure serial port
ser = serial.Serial(
    port='/dev/ttyS0',  # Default UART port on GPIO 14/15
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

# Set the static integer value to be sent
static_value = 42  # Modify this value as needed

try:
    while True:
        # Send static integer value as bytes (convert integer to byte format)
        ser.write(f"{static_value}\n".encode())  # Send the static integer value as a string
        print(f"Sent: {static_value}")

        time.sleep(5)

except KeyboardInterrupt:
    ser.close()
    print("Serial port closed.")
