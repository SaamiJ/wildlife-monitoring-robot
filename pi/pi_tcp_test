import socket

# Define the server's host and port
HOST = '0.0.0.0'  # Listen on all network interfaces
PORT = 5000

# Create a socket object to listen for incoming connections
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((HOST, PORT))  # Bind to the specified address and port
sock.listen(1)  # Wait for one connection (can be increased if needed)

print(f"Listening for connections on {HOST}:{PORT}")

# Accept an incoming connection
conn, addr = sock.accept()
print(f"Connected by {addr}")

# Main loop to handle incoming data from the laptop
while True:
    # Receive the data sent by the laptop (keypresses)
    data = conn.recv(1024).decode().strip()  # Max data size = 1024 bytes
    if not data:
        break  # If no data is received, break the loop
    
    print(f"Received command: {data}")  # Print the received command
    
    # Here, you would handle the command (e.g., forward, backward, etc.)
    # For now, we just print it to the console.

# Close the connection
conn.close()
