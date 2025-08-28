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

### Steps for running in Docker ### 
# 1. Install VcXsrv (https://vcxsrv.com/)
# 2. Start VcXsrv with the following options:
#       - Choose Multiple windows
#       - Set display number to 0
#       - Enable "disable access conrol"
#       - Click Next and Finish
# 3. Navigate to the GUI directory
# 4. Start Docker Desktop
# 5. Run "docker pull saamij/wildlife-gui:latest"
# 6. Run "docker run -e DISPLAY=host.docker.internal:0 --rm -v /tmp/.X11-unix:/tmp/.X11-unix wildlife-gui"

class GUI(tk.Tk):
    def __init__(self, camera=0):
        super().__init__()

        # Variable initializatio
        self.saved_image_count = 0
        self.cap = None
        self.camera_index = camera
        self._running = False
        self._imgtk_cache = None
        self.imageDir = os.path.expanduser("pi/GUI/stored_image")
        self.host = 'raspberrypi.local'
        self.port = 5000

        # calling layout window
        self.interface_layout()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.load_images_list()
        
        # checking for user input
        self.bind("<KeyPress>", self.keyboard_input)   # This handles key press events
        self.bind("<KeyRelease>", self.on_key_release)  # This handles key release events
        
    def interface_layout(self):
        self.title("Wildlife Monitoring Robot Interface")
        self.config(bg="white")

        # video area
        self.videoFrame = tk.Frame(self, width=960, height=540, bg="skyblue")
        self.videoFrame.grid(row=0, column=0, rowspan=3, columnspan=3, sticky="w", padx=10, pady=10)
        self.videoFrame.grid_propagate(False)
        self.videoLabel = tk.Label(self.videoFrame, text="Camera Video", bg="lightgray")
        self.videoLabel.grid(row=0, column=0, sticky="nw")

        #all the status area
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


        # list of saved images
        self.statusFrame = tk.Frame(self, width=300, height=370, bg="white")
        self.statusFrame.grid(row=1, column=3, rowspan=2, columnspan=2, sticky="w", padx=10, pady=10)
        self.statusFrame.grid_propagate(False)
        self.statusLabel = tk.Label(self.statusFrame, text="Saved Images:", bg="white", fg="black", font=("Arial", 22, "bold"))
        self.statusLabel.grid(row=0, column=0, sticky="nw", pady=10)
        self.imgList = tk.Listbox(self.statusFrame, activestyle="underline", width=23, height=10, bg="white", fg="black", font=("Arial", 20, "bold"),selectbackground="lightblue", selectforeground="black")
        self.imgList.grid(row=1, column=0, sticky="w")
        self.imgScroll = tk.Scrollbar(self.statusFrame, orient="vertical", command=self.imgList.yview)
        self.imgScroll.grid(row=1, column=1, sticky="ns", pady=8)
        self.imgList.config(yscrollcommand=self.imgScroll.set)
        self.imgList.bind("<Double-1>", self.open_selected_image)

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
                try:
                    self.sock.sendall(command.encode())
                    print(f"Sent command: {command}")
                except socket.error as e:
                    print(f"Error sending command: {e}")
            else:
                print("Socket not connected.")
        except:
            print("Socket error occurred while sending command.")
    
    def keyboard_input(self, event):
        # Check for key press actions (movement and controls)
        if event.char == 'w':
            self.btn_forward.invoke()  # Simulate button press
    
        if event.char == 's':  
            self.btn_back.invoke()
    
        if event.char == 'a':
            self.btn_left.invoke()
    
        if event.char == 'd':
            self.btn_right.invoke()
    
        if event.keysym == "space": 
            self.btn_stop.invoke()
        
        if event.keysym == "Tab":
            self.btn_start.invoke()
    
        if event.keysym == "Return":
            self.btn_save_image.invoke()
    
        if event.keysym == "Escape":
            self.on_close()
    
        if event.char == '=':
            self.increase_speed()
    
        if event.char == '-':
            self.decrease_speed()

    def on_key_release(self, event):
    if event.char in ['w', 'a', 's', 'd']:
        self.send_command('F000\n')
        self.movementStatus.config(text="Idle")

    def increase_speed(self):
        current_speed = self.speedSlider.get()
        new_speed = min(current_speed + 50, 999)
        self.speedSlider.set(new_speed)

    
    def decrease_speed(self):
        current_speed = self.speedSlider.get()
        new_speed = max(current_speed - 50, 300)
        self.speedSlider.set(new_speed)

    def move_forward(self):
        self.send_command(f'F{self.speedSlider.get()}\n')
        self.movementStatus.config(text="Forward")
        self.btn_forward.config(bg="lightgreen")
        print("Moving forward")
    
    def move_backward(self):
        self.send_command(f'B{self.speedSlider.get()}\n')
        self.movementStatus.config(text="Backward")
        self.btn_back.config(bg="lightgreen")
        print("Moving backward")  

    def turn_left(self):
        self.send_command(f'L{self.speedSlider.get()}\n')
        self.movementStatus.config(text="Left")
        self.btn_left.config(bg="lightgreen")
        print("Turning left")

    def turn_right(self):
        self.send_command(f'R{self.speedSlider.get()}\n')
        self.movementStatus.config(text="Right")
        self.btn_right.config(bg="lightgreen")
        print("Turning right")

    def stop_movement(self):
        self.send_command('STOP\n')
        self.movementStatus.config(text="Idle")
        print("Stopping movement")

    def start(self):
        if self._running:
            return
        # Open camera (0 = default webcam). For a network stream use a URL instead.
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open camera/stream.")
            return
        self._running = True
        self.after(0, self.update_frame)

    def stop_camera(self):
        self._running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def update_frame(self):
        if not self._running or not self.cap:
            return

        ok, frame = self.cap.read()
        frameStartTime = time.time()
        if ok:
            # BGR -> RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Fit to label while keeping aspect ratio
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
            # Try to recover on read failures
            self.stop_camera()
            self.start()
            return
        
        frameEndTime = time.time()
        timeDifference = frameEndTime - frameStartTime
        fps = 1 / timeDifference if timeDifference > 0 else 0
        self.fpsLabel.config(text=f"FPS: \t {fps:.1f}")

        # Schedule next frame (~30–33 ms ≈ 30 FPS)
        self.after(30, self.update_frame)

    def save_image(self):
        if not self.cap:
            messagebox.showinfo("Info", "Start the camera first.")
            return
        ok, frame = self.cap.read()
        if not ok:
            messagebox.showerror("Error", "Failed to capture frame.")
            return
        filename = f"pi/GUI/stored_image/image_{self.saved_image_count}.png"
        self.saved_image_count += 1
        cv2.imwrite(filename, frame)
        self.load_images_list()

    def on_close(self):
        self.stop_camera()
        self.destroy()
        if self.sock:
            try:
                self.sock.sendall(b'STOP\n')  # Send stop command
            except socket.error as e:
                print(f"Error sending stop command: {e}")
            self.sock.close()
            self.sock = None    

    
    
    def load_images_list(self):
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

    def open_selected_image(self, event=None):
        sel = self.imgList.curselection()
        if not sel:
            return
        path = self._img_files[sel[0]]
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as e:
            tk.messagebox.showerror("Open failed", f"Could not open:\n{path}\n\n{e}")

if __name__ == "__main__":
    # For a network stream (e.g., MJPEG from Pi), replace camera=0 with:
    # camera="http://<PI_IP>:8080/?action=stream"
    app = GUI(camera=0)
    app.mainloop()
