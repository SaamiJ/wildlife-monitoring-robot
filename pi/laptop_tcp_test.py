import socket
import keyboard

# Define the Pi Zero's IP address and port
HOST = 'raspberrypi.local'
PORT = 5000

# Create socket connection to Pi
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

print("Connected to Pi Zero 2. Use WASD to control direction. Use + and - for speed.")

speed = 500  # Initial speed (duty cycle from 0-1000)

while True:
    # Read keyboard input to control motor direction and speed
    if keyboard.is_pressed('w'):
        sock.sendall(f'F{speed}\n'.encode())  # Forward with current speed
    elif keyboard.is_pressed('s'):
        sock.sendall(f'B{speed}\n'.encode())  # Backward with current speed
    elif keyboard.is_pressed('a'):
        sock.sendall(f'L{speed}\n'.encode())  # Turn left
    elif keyboard.is_pressed('d'):
        sock.sendall(f'R{speed}\n'.encode())  # Turn right

    # Adjust speed dynamically with + and -
    elif keyboard.is_pressed('+') and speed < 1000:
        speed += 100
        print(f"Speed increased to {speed}")
    elif keyboard.is_pressed('-') and speed > 0:
        speed -= 100
        print(f"Speed decreased to {speed}")
    
    # Break on 'q'
    elif keyboard.is_pressed('q'):
        sock.sendall(b'STOP\n')  # Send stop command
        break

    while keyboard.is_pressed('+') or keyboard.is_pressed('-'):
        pass

sock.close()  # Close the socket