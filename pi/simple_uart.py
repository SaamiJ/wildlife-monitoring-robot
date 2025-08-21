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

direction = 'F'  # Direction can be 'F', 'B', 'L', 'R'
pwm_value = 700  # PWM value (0-1000)

try:
    while True:
        
        message = f"{direction}{pwm_value}\n"
        ser.write(message.encode())

        time.sleep(5)

except KeyboardInterrupt:
    ser.close()
    print("Serial port closed.")
