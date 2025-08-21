import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import time

class GUI(tk.Tk):
    def __init__(self, camera=0):
        super().__init__()
        self.interface_layout()
        self.saved_image_count = 0
        self.cap = None
        self.camera_index = camera
        self._running = False
        self._imgtk_cache = None

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.bind("<Key>", self.keyboard_input)
        self.bind("<Escape>", lambda e: self.on_close)
        self.bind("<Return>", lambda e: self.save_image)
        

    def interface_layout(self):
        self.title("Wildlife Monitoring Robot Interface")
        self.config(bg="white")

        self.videoFrame = tk.Frame(self, width=960, height=540, bg="skyblue")
        self.videoFrame.grid(row=0, column=0, rowspan=3, columnspan=3, sticky="w", padx=10, pady=10)
        self.videoFrame.grid_propagate(False)

        self.videoLabel = tk.Label(self.videoFrame, text="Camera Video", bg="lightgray")
        self.videoLabel.grid(row=0, column=0, sticky="nw")

        self.fpsFrame = tk.Frame(self, width=120, height=150, bg="white")
        self.fpsFrame.grid(row=0, column=3, sticky="e", padx=10, pady=10)
        self.fpsLabel = tk.Label(self.fpsFrame, text="FPS\t: 0", bg="white", fg="black", font=("Arial", 16, "bold"))
        self.fpsLabel.grid(row=0, column=0, sticky="nw", pady=20)
        self.leftWheelLabel = tk.Label(self.fpsFrame, text="Left Wheel (rpm)\t: ", bg="white", fg="black", font=("Arial", 16, "bold"))
        self.leftWheelLabel.grid(row=1, column=0, sticky="w", pady=5)
        self.rightWheelLabel = tk.Label(self.fpsFrame, text="Right Whee (rpm)\t: ", bg="white", fg="black", font=("Arial", 16, "bold"))
        self.rightWheelLabel.grid(row=2, column=0, sticky="w", pady=5)

        self.connectionStatusFrame = tk.Frame(self, width=120, height=150, bg="lightgray")
        self.connectionStatusFrame.grid(row=0, column=4, sticky="w", padx=10, pady=10)

        self.statusFrame = tk.Frame(self, width=300, height=150, bg="lightgray")
        self.statusFrame.grid(row=1, column=3, columnspan=2, sticky="w", padx=10, pady=10)
        self.statusFrame.grid_propagate(False)
        self.statusTitle = tk.Label(self.statusFrame, text="Robot Status Display", bg="lightgray", fg="black", font=("Arial", 16, "bold"))
        self.statusTitle.grid(row=0, column=0, sticky="nw", padx=10, pady=10)
        self.statusLabel = tk.Label(self.statusFrame, text="Status: Idle", bg="white", fg="black", font=("Arial", 14))
        self.statusLabel.grid(row=1, column=0, sticky="nw", padx=10, pady=10)

        self.alertFrame = tk.Frame(self, width=300, height=180, bg="lightgray")
        self.alertFrame.grid(row=2, column=3, columnspan=2, sticky="w", padx=10)

        self.speedFrame = tk.Frame(self, width=300, height=180, bg="white")
        self.speedFrame.grid(row=3, column=3, columnspan=2, sticky="nw", padx=10, pady=10)
        self.speedSlider = tk.Scale(
            self.speedFrame, from_=0, to=100, orient=tk.HORIZONTAL,
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
        self.btn_forward = tk.Button(self.movemenrtFrame, text="↑ Forward", width=8, height=4)
        self.btn_forward.grid(row=1, column=1, padx=5, pady=5)
        self.btn_left = tk.Button(self.movemenrtFrame, text="← Left", width=8, height=4)
        self.btn_left.grid(row=2, column=0, padx=5, pady=5)
        self.btn_stop = tk.Button(self.movemenrtFrame, text="■ Stop", width=8, height=4)
        self.btn_stop.grid(row=2, column=1, padx=5, pady=5)
        self.btn_right = tk.Button(self.movemenrtFrame, text="Right →", width=8, height=4)
        self.btn_right.grid(row=2, column=2, padx=5, pady=5)
        self.btn_back = tk.Button(self.movemenrtFrame, text="↓ Back", width=8, height=4)
        self.btn_back.grid(row=3, column=1, padx=5, pady=5)

        # Camera Control
        self.cameraControlFrame = tk.Frame(self, width=400, height=400, bg="white")
        self.cameraControlFrame.grid(row=3, column=1, sticky="w", padx=10, pady=10)
        self.cameraControlLabel = tk.Label(self.cameraControlFrame, text="Camera Control:", bg="white", fg="black", font=("Arial", 16, "bold"))
        self.cameraControlLabel.grid(row=0, column=0, sticky="nw")
        self.btn_start = ttk.Button(self.cameraControlFrame, text="Start Camera", width=12, command=self.start)
        self.btn_start.grid(row=1, column=0, padx=5, pady=5)
        self.btn_stop_camera = ttk.Button(self.cameraControlFrame, text="Stop Camera", width=12, command=self.stop)
        self.btn_stop_camera.grid(row=1, column=1, padx=5, pady=5)
        self.btn_save_image = ttk.Button(self.cameraControlFrame, text="Save Image", width=12, command=self.save_image)
        self.btn_save_image.grid(row=1, column=2, padx=5, pady=5)
    
    def keyboard_input(self, event):
        if event.char == 'w':
            print("Move forward")

        if event.char == 's':
            print("Move backward")

        if event.char == 'a':
            self.start()
            print("Turn left")

        if event.char == 'd':
            print("Turn right")

        if event.char == 'space':
            print("Stop")

    def start(self):
        if self._running:
            return
        # Open camera (0 = default webcam). For a network stream use a URL instead.
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Could not open camera/stream.")
            return
        self._running = True
        self.after(0, self._update_frame)

    def stop(self):
        self._running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def _update_frame(self):
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
            self.stop()
            self.start()
            return
        
        frameEndTime = time.time()
        timeDifference = frameEndTime - frameStartTime
        fps = 1 / timeDifference if timeDifference > 0 else 0
        self.fpsLabel.config(text=f"FPS: \t {fps:.1f}")


        # Schedule next frame (~30–33 ms ≈ 30 FPS)
        self.after(30, self._update_frame)

    def save_image(self):
        if not self.cap:
            messagebox.showinfo("Info", "Start the camera first.")
            return
        ok, frame = self.cap.read()
        if not ok:
            messagebox.showerror("Error", "Failed to capture frame.")
            return
        filename = f"image_{self.saved_image_count}.png"
        self.saved_image_count += 1
        cv2.imwrite(filename, frame)

    def on_close(self):
        self.stop()
        self.destroy()

if __name__ == "__main__":
    # For a network stream (e.g., MJPEG from Pi), replace camera=0 with:
    # camera="http://<PI_IP>:8080/?action=stream"
    app = GUI(camera=0)
    app.mainloop()
