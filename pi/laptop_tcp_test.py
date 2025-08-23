import socket
import keyboard

# Define the Pi Zero's IP address and port
HOST = '172.20.10.5'
PORT = 5000

# Create socket connection to Pi
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

print("Connected to Pi Zero 2. Use WASD to control direction. Use + and - for speed.")

speed = 500  # Initial speed (duty cycle from 0-999)

while True:
    # Read keyboard input to control motor direction and speed
    if keyboard.is_pressed('w'):
        sock.sendall(f'F{speed}\n'.encode())  # Forward
    
    elif keyboard.is_pressed('s'):
        sock.sendall(f'B{speed}\n'.encode())  # Backward
    
    elif keyboard.is_pressed('a'):
        sock.sendall(f'L{speed}\n'.encode())  # Left
    
    elif keyboard.is_pressed('d'):
        sock.sendall(f'R{speed}\n'.encode())  # Right

    # Adjust speed dynamically with + and -
    elif keyboard.is_pressed('+') and speed < 999:
        speed += 50
        if speed > 999:
            speed = 999
        print(f"Speed increased to {speed}")

    elif keyboard.is_pressed('-') and speed > 0:
        speed -= 50
        if speed < 0:
            speed = 0
        print(f"Speed decreased to {speed}")
    
    # Break on 'q'
    elif keyboard.is_pressed('q'):
        sock.sendall(b'STOP\n')
        break

    while keyboard.is_pressed('+') or keyboard.is_pressed('-'):
        pass

sock.close()  # Close the socket