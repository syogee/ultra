import socket
import threading
import json
import time
import struct
import io
from queue import Queue

import mss
from PIL import Image
import pyautogui

from protocol import send_msg, recv_msg, MsgType

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0


class HostService:
    def __init__(self, host_id, password, relay_host='127.0.0.1', relay_port=9999):
        self.host_id = str(host_id)
        self.password = str(password)
        self.relay_host = relay_host
        self.relay_port = relay_port

        self.running = False
        self.sock = None

        self.send_queue = Queue()

        self.quality = 60
        self.resize_factor = 0.7
        self.fps_cap = 15

    # ---------------- START / STOP ----------------

    def start(self):
        self.running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

    # ---------------- MAIN LOOP ----------------

    def _run(self):
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(5)
                self.sock.connect((self.relay_host, self.relay_port))
                self.sock.settimeout(None)

                reg = {
                    "id": self.host_id,
                    "password": self.password
                }
                send_msg(self.sock, MsgType.REGISTER_HOST, json.dumps(reg).encode())

                print(f"[Host] Connected: {self.host_id}")

                # start threads
                threading.Thread(target=self._screen_loop, daemon=True).start()
                threading.Thread(target=self._sender_loop, daemon=True).start()

                self._input_loop()

            except Exception as e:
                print("[Host] reconnecting...", e)
                time.sleep(3)

    # ---------------- SCREEN CAPTURE ----------------

    def _screen_loop(self):
        with mss.mss() as sct:
            mon = sct.monitors[1]

            while self.running:
                try:
                    img = sct.grab(mon)
                    frame = Image.frombytes("RGB", img.size, img.rgb)

                    nw = int(img.width * self.resize_factor)
                    nh = int(img.height * self.resize_factor)
                    frame = frame.resize((nw, nh))

                    buf = io.BytesIO()
                    frame.save(buf, format="JPEG", quality=self.quality)

                    header = struct.pack("!HH", img.width, img.height)
                    self.send_queue.put(header + buf.getvalue())

                except:
                    break

                time.sleep(1 / self.fps_cap)

    # ---------------- NETWORK SENDER (ONLY SOCKET USER) ----------------

    def _sender_loop(self):
        while self.running and self.sock:
            try:
                data = self.send_queue.get()
                send_msg(self.sock, MsgType.SCREEN_FRAME, data)
            except:
                break

    # ---------------- INPUT RECEIVER ----------------

    def _input_loop(self):
        while self.running and self.sock:
            try:
                msg_type, payload = recv_msg(self.sock)

                if msg_type is None:
                    break

                if msg_type == MsgType.MOUSE_EVENT:
                    e = json.loads(payload.decode())

                    if e["action"] == "move":
                        pyautogui.moveTo(e["x"], e["y"])

                    elif e["action"] == "click":
                        pyautogui.click(e["x"], e["y"])

                    elif e["action"] == "right":
                        pyautogui.rightClick()

                elif msg_type == MsgType.KEY_EVENT:
                    e = json.loads(payload.decode())
                    pyautogui.press(e["key"])

            except Exception:
                break