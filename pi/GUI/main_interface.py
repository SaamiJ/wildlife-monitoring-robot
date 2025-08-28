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

        # Video area, status area, and control layout remain unchanged...
        # (Code for interface layout remains as in the previous snippet)

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

    def send_command(self, command):
        """Send a command to the robot."""
        try:
            if self.sock:
                self.sock.sendall(command.encode())
                print(f"Sent command: {command}")
            else:
                print("Socket not connected.")
        except Exception as e:
            print(f"Error sending command: {e}")
    
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
