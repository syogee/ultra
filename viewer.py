import socket
import threading
import json
import struct
import cv2
import numpy as np
import tkinter as tk
import time
from PIL import Image, ImageTk

from protocol import send_msg, recv_msg, MsgType


class ViewerWindow:
    def __init__(self, target_id, password, relay_host='127.0.0.1', relay_port=9999):
        self.target_id = str(target_id)
        self.password = str(password)
        self.relay_host = relay_host
        self.relay_port = relay_port

        self.sock = None
        self.running = False

        self.host_width = 1280
        self.host_height = 720

        self.last_move = 0

        self.root = tk.Toplevel()
        self.root.title(f"Viewer - {self.target_id}")
        self.root.geometry("1280x720")

        self.canvas = tk.Canvas(self.root, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.img_id = None
        self.tk_img = None

        self._bind_events()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    # ---------------- CONNECT ----------------

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)  # IMPORTANT FIX

            self.sock.connect((self.relay_host, self.relay_port))
            self.sock.settimeout(None)

            reg = {
                "id": self.target_id,
                "password": self.password
            }

            send_msg(self.sock, MsgType.REGISTER_VIEWER, json.dumps(reg).encode())

            msg_type, payload = recv_msg(self.sock)
            if msg_type != MsgType.AUTH_RESP:
                self.close()
                return

            resp = json.loads(payload.decode())

            if resp.get("status") != "ok":
                print("[Viewer] Auth failed")
                self.close()
                return

            self.running = True
            print("[Viewer] Connected")

            threading.Thread(target=self._recv_loop, daemon=True).start()

        except Exception as e:
            print("[Viewer] Connect error:", e)
            self.close()

    # ---------------- RECEIVE THREAD ----------------

    def _recv_loop(self):
        while self.running and self.sock:
            try:
                self.sock.settimeout(5)

                msg_type, payload = recv_msg(self.sock)

                if msg_type is None:
                    break

                if msg_type == MsgType.SCREEN_FRAME:
                    self.host_width, self.host_height = struct.unpack("!HH", payload[:4])
                    img = payload[4:]

                    np_arr = np.frombuffer(img, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                    if frame is not None:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        self.root.after(0, self._update_image, frame)  # SAFE FIX

            except socket.timeout:
                continue
            except Exception as e:
                print("[Viewer] recv error:", e)
                break

        self.root.after(0, self.close)

    # ---------------- UI UPDATE (SAFE) ----------------

    def _update_image(self, frame):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w < 2 or h < 2:
            return

        frame = cv2.resize(frame, (w, h))

        img = Image.fromarray(frame)
        self.tk_img = ImageTk.PhotoImage(img)

        if self.img_id is None:
            self.img_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        else:
            self.canvas.itemconfig(self.img_id, image=self.tk_img)

    # ---------------- INPUT EVENTS ----------------

    def _bind_events(self):
        self.canvas.bind("<Motion>", self._mouse_move)
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<Button-3>", self._right_click)
        self.root.bind("<Key>", self._key)

        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set(), add='+')

    def _map(self, x, y):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        if cw < 2 or ch < 2:
            return 0, 0

        return int(x / cw * self.host_width), int(y / ch * self.host_height)

    def _send(self, data):
        try:
            if self.sock:
                send_msg(self.sock, MsgType.MOUSE_EVENT, json.dumps(data).encode())
        except:
            pass

    def _mouse_move(self, e):
        now = time.time()
        if now - self.last_move < 0.03:  # throttle (~30fps)
            return

        x, y = self._map(e.x, e.y)
        self.last_move = now

        self._send({"action": "move", "x": x, "y": y})

    def _click(self, e):
        x, y = self._map(e.x, e.y)
        self._send({"action": "click", "x": x, "y": y, "button": "left"})

    def _right_click(self, e):
        x, y = self._map(e.x, e.y)
        self._send({"action": "click", "x": x, "y": y, "button": "right"})

    def _key(self, e):
        self._send({"key": e.keysym})

    # ---------------- CLOSE ----------------

    def close(self):
        self.running = False

        try:
            if self.sock:
                self.sock.close()
        except:
            pass

        self.root.destroy()