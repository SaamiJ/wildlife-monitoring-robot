import socket
import time
import struct
import numpy as np
import cv2
import threading
import queue
from datetime import datetime
import torch
import os
from ultralytics import YOLO
from collections import deque

MODEL_PATH = "laptop/best.pt"

class VideoClient(threading.Thread):
    def __init__(
        self,
        server_ip,
        server_port,
        animal_names,
        conf_threshold=0.80,
        iou_threshold=0.45,
        imgsz=640,
        draw_threshold=None,         # threshold for drawing/Publishing
        annotate=True,               # turn off to save a few ms per frame
        label_name="video_stream",   # goes into d_names
        publish_keep=200,            # ring-buffer size for GUI variables
    ):
        super().__init__(daemon=True)
        self.server_ip = server_ip
        self.server_port = server_port
        self.animal_names = animal_names
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        self.annotate = bool(annotate)
        self.label_name = str(label_name)
        self.draw_threshold = self.conf_threshold if draw_threshold is None else float(draw_threshold)

        self.sock = None
        self.running = True
        self.frame_queue = queue.Queue(maxsize=10)

        self._last_t = None
        self._fps = 0.0
        self._ema_alpha = 0.90

        # ---- PUBLIC: in-memory detections for GUI (thread-safe) ----
        # Read these four from the GUI. No CSV middle-man anymore.
        self.v_lock    = threading.Lock()
        self.v_times   = deque(maxlen=publish_keep)  # e.g., "2025-10-08T20:51:03"
        self.v_animals = deque(maxlen=publish_keep)  # class names
        self.v_scores  = deque(maxlen=publish_keep)  # confidences (float)
        self.v_names   = self.label_name             # template/label string

        # Device selection
        if torch.backends.mps.is_available():
            device = torch.device("mps")
        elif torch.cuda.is_available():
            device = torch.device("cuda")
        else:
            device = torch.device("cpu")
        self.device = device

        # Load model
        self.model = YOLO(MODEL_PATH)
        self.model.model.float()
        self.model.fuse()
        self.model.to(self.device)
        print(f"Loaded YOLO model on {self.device}")

        # Use smaller image size
        self.imgsz = 416
        try:
            path = MODEL_PATH if os.path.exists(MODEL_PATH) else "best.pt"
            if not os.path.exists(path):
                raise FileNotFoundError(f"Cannot find YOLO model at: {MODEL_PATH} or best.pt")
            self.model = YOLO(path)
            # Try to fuse for a small inference speedup; ignore if not supported
            try:
                self.model.fuse()
            except Exception:
                pass
            print(f"Loaded YOLO model from {path} on device {self.device}")
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            self.model = None

    # ----- utility -----
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
        text = f"{fps:.1f} FPS"
        if not self.annotate:
            return
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.6
        thickness = 2
        pad = 8
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
        h, w = frame.shape[:2]
        x2 = w - pad
        y1 = pad
        x1 = x2 - tw - 2*pad
        y2 = y1 + th + 2*pad
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
        cv2.putText(frame, text, (x1 + pad, y2 - pad - baseline), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

    def _class_name(self, cls_id: int) -> str:
        if isinstance(self.animal_names, dict):
            return self.animal_names.get(cls_id, str(cls_id))
        if isinstance(self.animal_names, (list, tuple)) and 0 <= cls_id < len(self.animal_names):
            return self.animal_names[cls_id]
        return str(cls_id)

    # ----- detection -----
    def _detect_and_annotate(self, frame):
        if self.model is None:
            return []

        results = self.model.predict(
            source=frame,
            imgsz=self.imgsz,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
            device=self.device
        )

        dets = []
        r = results[0]
        boxes = getattr(r, "boxes", None)
        if boxes is None or boxes.xyxy is None:
            return dets

        # Move to CPU once, then lightweight loops
        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()
        clss = boxes.cls.cpu().numpy().astype(int)

        for (x1, y1, x2, y2), conf, cls_id in zip(xyxy, confs, clss):
            if float(conf) < self.draw_threshold:
                continue

            name = self._class_name(cls_id)
            dets.append((name, float(conf)))

            if self.annotate:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{name} {conf:.2f}", (x1, max(0, y1-8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Publish (no CSV writes)
        if dets:
            ts = datetime.now().isoformat(timespec='seconds')
            with self.v_lock:
                for name, conf in dets:
                    self.v_times.append(ts)
                    self.v_animals.append(name)
                    self.v_scores.append(round(float(conf), 3))
                # d_names is a string label; keep as-is

        return dets

    # Optional helper for GUI: returns snapshot copies (thread-safe)
    def get_latest(self, n=10):
        with self.v_lock:
            return {
                "times": list(self.v_times)[-n:],
                "animals": list(self.v_animals)[-n:],
                "scores": list(self.v_scores)[-n:],
                "name": self.v_names,
            }

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.server_ip, self.server_port))
            print("Connected to Pi Zero 2 W video server")
        except socket.error as e:
            print(f"Connection error: {e}")
            self.sock = None

    # ----- main loop -----
    def run(self):
        buf = b''

        try:
            while self.running:
                # read 4-byte length
                while len(buf) < 4:
                    more = self.sock.recv(4096)
                    if not more:
                        raise ConnectionError("Connection closed by server")
                    buf += more
                msg_len = struct.unpack(">I", buf[:4])[0]
                buf = buf[4:]

                # read payload
                while len(buf) < msg_len:
                    more = self.sock.recv(4096)
                    if not more:
                        raise ConnectionError("Connection closed by server")
                    buf += more

                frame_data = buf[:msg_len]
                buf = buf[msg_len:]

                # decode JPEG/PNG -> BGR frame
                frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                fps = self._update_fps()
                self._draw_fps(frame, fps)

                self._detect_and_annotate(frame)

                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
        except Exception as e:
            print(f"VideoClient error: {e}")
        finally:
            try:
                self.sock.close()
            except Exception:
                pass

    def stop(self):
        self.running = False