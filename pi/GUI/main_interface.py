import os
import sys
import subprocess
import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import time
import socket

class GUI(tk.Tk):
    def __init__(self, camera=0):
        super().__init__()

        # Variable initialization
        self.saved_image_count = 0
        self.cap = None
        self.camera_index = camera
        self._running = False
        self._imgtk_cache = None
        self.imageDir = os.path.expanduser("pi/GUI/stored_image")
        self.host = 'raspberrypi.local'
        self.port = 5000

        # Movement control variables
        self.speed = 500  # Initial speed
        self.prev_dir = None  # 'F', 'B', 'L', 'R', or None (idle)

        # calling layout window
        self.interface_layout()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.load_images_list()

        # Bind key events for movement and control
        self.bind("<KeyPress>", self.on_key_press)
        self.bind("<KeyRelease>", self.on_key_release)

    def interface_layout(self):
        self.title("Wildlife Monitoring Robot Interface")
        self.config(bg="white")

        # video area
        self.videoFrame = tk.Frame(self, width=960, height=540, bg="skyblue")
        self.videoFrame.grid(row=0, column=0, rowspan=3, columnspan=3, sticky="w", padx=10, pady=10)
        self.videoFrame.grid_propagate(False)
        self.videoLabel = tk.Label(self.videoFrame, text="Camera Video", bg="lightgray")
        self.videoLabel.grid(row=0, column=0, sticky="nw")

        # all the status area
        self.fpsFrame = tk.Frame(self, width=120, height=150, bg="white")
        self.fpsFrame.grid(row=0, column=3, sticky="e", padx=10, pady=10)
        self.fpsLabel = tk.Label(self.fpsFrame, text="FPS\t: 0", bg="white", fg="black", font=("Arial", 14, "bold"))
        self.fpsLabel.grid(row=0, column=0, sticky="nw", pady=20)
        self.leftWheelLabel = tk.Label(self.fpsFrame, text="Left Wheel (rpm)\t: ", bg="white", fg="black", font=("Arial", 14, "bold"))
        self.leftWheelLabel.grid(row=1, column=0, sticky="w", pady=5)
        self.rightWheelLabel = tk.Label(self.fpsFrame, text="Right Whee (rpm)\t: ", bg="white", fg="black", font=("Arial", 14, "bold"))
        self.rightWheelLabel.grid(row=2, column=0, sticky="w", pady=5)

        # info area
        self.connectionStatusFrame = tk.Frame(self, width=120, height=150, bg="white")
        self.connectionStatusFrame.grid(row=0, column=4, sticky="w", padx=10, pady=10)
        self.connectionStatusLabelTitle = tk.Label(self.connectionStatusFrame, text="Status:", bg="white", fg="black", font=("Arial", 14, "bold"))
        self.connectionStatusLabelTitle.grid(row=0, column=0, sticky="nw")
        self.connectionStatusLabel = tk.Label(self.connectionStatusFrame, text="Disconnected", bg="white", fg="red", font=("Arial", 14, "bold"))
        self.connectionStatusLabel.grid(row=1, column=0, sticky="nw")
        self.movementStatus = tk.Label(self.connectionStatusFrame, text="\nIdle", bg="white", fg="black", font=("Arial", 14, "bold"))
        self.movementStatus.grid(row=2, column=0, sticky="s")
        self.connectButton = ttk.Button(self.connectionStatusFrame, text="Connect", command=self.connection_setup, width=7)
        self.connectButton.grid(row=3, column=0, padx=5, pady=5)

        # Speed Scroll
        self.speedFrame = tk.Frame(self, width=300, height=180, bg="white")
        self.speedFrame.grid(row=3, column=3, columnspan=2, sticky="nw", padx=10, pady=10)
        self.speedSlider = tk.Scale(
            self.speedFrame, from_=300, to=999, orient=tk.HORIZONTAL,
            label="Speed Control", bg="white", fg="black",
            font=("Arial", 16, "bold"), length=280
        )
        self.speedSlider.set(50)  # Set initial value to 50
        self.speedSlider.grid(row=0, column=0, padx=10, pady=10)

        # Movement Control
        self.movemenrtFrame = tk.Frame(self, width=400, height=400, bg="white")
        self.movemenrtFrame.grid(row=3, column=0, sticky="w", padx=10, pady=10)
        self.movementLabel = tk.Label(self.movemenrtFrame, text="Movement Control:", bg="white", fg="black", font=("Arial", 16, "bold"))
        self.movementLabel.grid(row=0, column=0, sticky="nw")
        self.btn_forward = tk.Button(self.movemenrtFrame, text="↑ Forward", command=self.move_forward, width=8, height=4)
        self.btn_forward.grid(row=1, column=1, padx=5, pady=5)
        self.btn_left = tk.Button(self.movemenrtFrame, text="← Left", command=self.turn_left, width=8, height=4)
        self.btn_left.grid(row=2, column=0, padx=5, pady=5)
        self.btn_stop = tk.Button(self.movemenrtFrame, text="■ Stop", command=self.stop_movement, width=8, height=4)
        self.btn_stop.grid(row=2, column=1, padx=5, pady=5)
        self.btn_right = tk.Button(self.movemenrtFrame, text="Right →", command=self.turn_right, width=8, height=4)
        self.btn_right.grid(row=2, column=2, padx=5, pady=5)
        self.btn_back = tk.Button(self.movemenrtFrame, text="↓ Back", command=self.move_backward, width=8, height=4)
        self.btn_back.grid(row=3, column=1, padx=5, pady=5)

        # Camera Control
        self.cameraControlFrame = tk.Frame(self, width=400, height=400, bg="white")
        self.cameraControlFrame.grid(row=3, column=1, sticky="w", padx=10, pady=10)
        self.cameraControlLabel = tk.Label(self.cameraControlFrame, text="Camera Control:", bg="white", fg="black", font=("Arial", 16, "bold"))
        self.cameraControlLabel.grid(row=0, column=0, sticky="nw")
        self.btn_start = tk.Button(self.cameraControlFrame, text="Start Camera", width=12, height=2, command=self.start)
        self.btn_start.grid(row=1, column=0, padx=5, pady=5)
        self.btn_stop_camera = tk.Button(self.cameraControlFrame, text="Stop Camera", width=12, height=2, command=self.stop_camera)
        self.btn_stop_camera.grid(row=1, column=1, padx=5, pady=5)
        self.btn_save_image = tk.Button(self.cameraControlFrame, text="Save Image", width=12, height=2, command=self.save_image)
        self.btn_save_image.grid(row=1, column=2, padx=5, pady=5)

    def connection_setup(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connectionStatusLabel.config(text="Connected", fg="green")
            print("Connected to Pi Zero 2")
        except socket.error as e:
            self.connectionStatusLabel.config(text=f"Error: {e}", fg="red")
            print(f"Connection error: {e}")
            self.sock = None

    def send_command(self, command):
        try:
            if self.sock:
                self.sock.sendall(command.encode())
                print(f"Sent command: {command}")
            else:
                print("Socket not connected.")
        except:
            print("Socket error occurred while sending command.")
    
    def on_key_press(self, event):
        """Handles key press events for movement control."""
        if event.char == 'w':
            self.move_forward()
        elif event.char == 's':
            self.move_backward()
        elif event.char == 'a':
            self.turn_left()
        elif event.char == 'd':
            self.turn_right()
        elif event.char == '+':
            self.increase_speed()
        elif event.char == '-':
            self.decrease_speed()
        elif event.char == ' ':
            self.stop_movement()

    def on_key_release(self, event):
        """Handles key release events to stop movement when no keys are pressed."""
        if event.char in ['w', 'a', 's', 'd']:
            self.stop_movement()

    def move_forward(self):
        """Send forward command to robot."""
        self.send_command(f'F{self.speed}\n')
        self.prev_dir = 'F'
        self.movementStatus.config(text="Moving Forward")
        print("Moving forward")

    def move_backward(self):
        """Send backward command to robot."""
        self.send_command(f'B{self.speed}\n')
        self.prev_dir = 'B'
        self.movementStatus.config(text="Moving Backward")
        print("Moving backward")

    def turn_left(self):
        """Send left turn command to robot."""
        self.send_command(f'L{self.speed}\n')
        self.prev_dir = 'L'
        self.movementStatus.config(text="Turning Left")
        print("Turning left")

    def turn_right(self):
        """Send right turn command to robot."""
        self.send_command(f'R{self.speed}\n')
        self.prev_dir = 'R'
        self.movementStatus.config(text="Turning Right")
        print("Turning right")

    def stop_movement(self):
        """Stop the robot."""
        self.send_command('F000\n')  # Send stop command with 0 speed (F000)
        self.prev_dir = None
        self.movementStatus.config(text="Idle")
        print("Stopping movement")

    def increase_speed(self):
        """Increase the robot's speed."""
        current_speed = self.speed
        new_speed = min(current_speed + 50, 999)
        self.speed = new_speed
        print(f"Speed increased to {self.speed}")

    def decrease_speed(self):
        """Decrease the robot's speed."""
        current_speed = self.speed
        new_speed = max(current_speed - 50, 0)
        self.speed = new_speed
        print(f"Speed decreased to {self.speed}")

    def on_close(self):
        """Handle closing the application."""
        self.stop_camera()
        self.destroy()
        if self.sock:
            try:
                self.sock.sendall(b'STOP\n')  # Send stop command when closing
            except socket.error as e:
                print(f"Error sending stop command: {e}")
            self.sock.close()
            self.sock = None    

    def load_images_list(self):
        """Load the list of saved images."""
        exts = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff")
        try:
            names = [f for f in os.listdir(self.imageDir) if f.lower().endswith(exts)]
        except FileNotFoundError:
            names = []
        names.sort()
        self._img_files = [os.path.join(self.imageDir, f) for f in names]
        self.imgList.delete(0, tk.END)
        for name in names:
            self.imgList.insert(tk.END, name)

    def start(self):
        """Start the camera feed."""
        if self._running:
            return
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open camera/stream.")
            return
        self._running = True
        self.after(0, self.update_frame)

    def stop_camera(self):
        """Stop the camera feed."""
        self._running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def update_frame(self):
        """Update the video frame."""
        if not self._running or not self.cap:
            return

        ok, frame = self.cap.read()
        if ok:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = frame.shape
            Lw = self.videoFrame.winfo_width() or 1
            Lh = self.videoFrame.winfo_height() or 1
            scale = min(Lw / w, Lh / h)
            new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

            img = Image.fromarray(frame)
            self._imgtk_cache = ImageTk.PhotoImage(image=img)
            self.videoLabel.configure(image=self._imgtk_cache)
        else:
            self.stop_camera()
            self.start()
            return
        
        self.after(30, self.update_frame)

if __name__ == "__main__":
    app = GUI(camera=0)
    app.mainloop()
