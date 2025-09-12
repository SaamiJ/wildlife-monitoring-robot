# video_client.py own by ECE4191 Team E08

import socket
import struct
import numpy as np
import cv2
import threading
import queue
import csv
import time
from datetime import datetime

class VideoClient(threading.Thread):
    def __init__(self, server_ip, server_port, animal_names, conf_threshold=0.5, log_file="laptop/detections_log.csv"):
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port
        self.animal_names = animal_names
        self.conf_threshold = conf_threshold
        self.log_file = log_file

        self.sock = None
        self.running = True
        self.frame_queue = queue.Queue(maxsize=10)

        # --- FPS additions ---
        self._last_t = None
        self._fps = 0.0
        self._ema_alpha = 0.90  # smoothing (0=no smooth, →1 = more smooth)

        # Initialize CSV log file, write header
        with open(self.log_file, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "animal", "confidence"])

    def _update_fps(self):
        now = time.perf_counter()
        if self._last_t is None:
            self._last_t = now
            return self._fps
        dt = now - self._last_t
        self._last_t = now
        if dt > 0:
            inst = 1.0 / dt
            self._fps = (self._ema_alpha * self._fps) + ((1.0 - self._ema_alpha) * inst) if self._fps > 0 else inst
        return self._fps

    def _draw_fps(self, frame, fps):
        # Format text
        text = f"{fps:.1f} FPS"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.6
        thickness = 2
        pad = 8

        # Measure text size
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
        h, w = frame.shape[:2]

        # Top-right box coordinates
        x2 = w - pad
        y1 = pad
        x1 = x2 - tw - 2*pad
        y2 = y1 + th + 2*pad

        # Box background for readability
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)

        # Put text
        cv2.putText(frame, text, (x1 + pad, y2 - pad - baseline), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.server_ip, self.server_port))
            self.connectionStatusLabel.config(text="Connected", fg="green")
            print("Connected to Pi Zero 2 W video server")
        except socket.error as e:
            self.connectionStatusLabel.config(text=f"Error: {e}", fg="red")
            print(f"Connection error: {e}")
            self.sock = None

    def run(self):
        # Connect to Pi video stream server
        data_buffer = b''

        try:
            while self.running:
                # Read message length (4 bytes)
                while len(data_buffer) < 4:
                    more = self.sock.recv(4096)
                    if not more:
                        raise ConnectionError("Connection closed by server")
                    data_buffer += more
                msg_len = struct.unpack(">I", data_buffer[:4])[0]
                data_buffer = data_buffer[4:]

                # Read frame data
                while len(data_buffer) < msg_len:
                    more = self.sock.recv(4096)
                    if not more:
                        raise ConnectionError("Connection closed by server")
                    data_buffer += more

                frame_data = data_buffer[:msg_len]
                data_buffer = data_buffer[msg_len:]

                # Decode JPEG frame (BGR)
                frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                # --- FPS update & draw ---
                fps = self._update_fps()
                self._draw_fps(frame, fps)

                #### MODEL HERE (I think) ####

                # Put frame into queue for GUI display (drop frame if queue full)
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)

        except Exception as e:
            print(f"VideoClient error: {e}")
        finally:
            self.sock.close()

    def stop(self):
        self.running = False
