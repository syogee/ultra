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

# Tkinter key to pyautogui key mapping
KEY_MAP = {
    'Return': 'enter', 'Escape': 'esc', 'BackSpace': 'backspace',
    'Tab': 'tab', 'space': 'space', 'Delete': 'delete',
    'Up': 'up', 'Down': 'down', 'Left': 'left', 'Right': 'right',
    'Home': 'home', 'End': 'end', 'Prior': 'pageup', 'Next': 'pagedown',
    'Control_L': 'ctrl', 'Control_R': 'ctrl',
    'Alt_L': 'alt', 'Alt_R': 'alt',
    'Shift_L': 'shift', 'Shift_R': 'shift',
    'Caps_Lock': 'capslock',
    'F1': 'f1', 'F2': 'f2', 'F3': 'f3', 'F4': 'f4',
    'F5': 'f5', 'F6': 'f6', 'F7': 'f7', 'F8': 'f8',
    'F9': 'f9', 'F10': 'f10', 'F11': 'f11', 'F12': 'f12',
}

SENDABLE = {
    'enter', 'esc', 'backspace', 'tab', 'space', 'delete',
    'up', 'down', 'left', 'right', 'home', 'end',
    'pageup', 'pagedown', 'ctrl', 'alt', 'shift', 'capslock',
    'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8',
    'f9', 'f10', 'f11', 'f12',
}

class ViewerWindow:
    def __init__(self, target_id, password, relay_host='127.0.0.1', relay_port=9999):
        self.target_id = str(target_id)
        self.password = str(password)
        self.relay_host = relay_host
        self.relay_port = relay_port
        
        self.sock = None
        self.running = False
        self.host_width = 1920
        self.host_height = 1080
        
        self._last_move = 0
        self._last_pos = None
        
        self.root = tk.Toplevel()
        self.root.title(f"Ultra Python Viewer - Connected to {self.target_id}")
        self.root.geometry("1280x720")
        
        self.canvas = tk.Canvas(self.root, bg="black", cursor="dot")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.image_on_canvas = None
        self.tk_img = None
        
        self._bind_events()
        
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        
    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.relay_host, self.relay_port))
            
            # Register as viewer
            reg_info = {'id': self.target_id, 'password': self.password}
            send_msg(self.sock, MsgType.REGISTER_VIEWER, json.dumps(reg_info).encode())
            
            msg_type, payload = recv_msg(self.sock)
            if msg_type == MsgType.AUTH_RESP:
                resp = json.loads(payload.decode('utf-8'))
                if resp['status'] != 'ok':
                    print(f"[Viewer] Auth failed: {resp['msg']}")
                    self.close()
                    return
            else:
                self.close()
                return
                
            self.running = True
            print("[Viewer] Connected successfully!")
            
            # Start recv thread
            self.recv_thread = threading.Thread(target=self._recv_frames)
            self.recv_thread.daemon = True
            self.recv_thread.start()
            
        except Exception as e:
            print(f"[Viewer] Connection error: {e}")
            self.close()

    def _recv_frames(self):
        while self.running and self.sock:
            try:
                msg_type, payload = recv_msg(self.sock)
                if msg_type is None or msg_type == MsgType.DISCONNECT:
                    print("[Viewer] Connection closed by host.")
                    self.root.after(0, self.close)
                    break
                    
                if msg_type == MsgType.SCREEN_FRAME:
                    # Unpack header
                    self.host_width, self.host_height = struct.unpack('!HH', payload[:4])
                    img_data = payload[4:]
                    
                    # Decode JPEG
                    np_arr = np.frombuffer(img_data, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        self._update_image(frame)
                        
            except Exception as e:
                print(f"[Viewer] Recv error: {e}")
                self.root.after(0, self.close)
                break

    def _update_image(self, frame):
        # Resize to fit canvas
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w > 1 and canvas_h > 1:
            frame = cv2.resize(frame, (canvas_w, canvas_h))
            
        img = Image.fromarray(frame)
        self.tk_img = ImageTk.PhotoImage(image=img)
        
        if self.image_on_canvas is None:
            self.image_on_canvas = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        else:
            self.canvas.itemconfig(self.image_on_canvas, image=self.tk_img)

    def _bind_events(self):
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonPress>", self._on_mouse_press)
        # Remove ButtonRelease since pyautogui click handles down/up
        self.canvas.bind("<Double-Button-1>", self._on_mouse_double_click)
        self.canvas.bind("<MouseWheel>", self._on_mouse_scroll)
        self.root.bind("<Key>", self._on_key_press) # Use <Key> for single press events instead of press/release
        
        # Focus on click so keys work
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set(), add='+')

    def _map_coords(self, event_x, event_y):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w < 1 or canvas_h < 1:
            return 0, 0
            
        x = int((event_x / canvas_w) * self.host_width)
        y = int((event_y / canvas_h) * self.host_height)
        return x, y

    def _send_mouse(self, action, x, y, button=None, dx=0, dy=0):
        if not self.running or not self.sock: return
        event = {'action': action, 'x': x, 'y': y}
        if button: event['button'] = button
        if dx or dy: 
            event['dx'] = dx
            event['dy'] = dy
            
        try:
            send_msg(self.sock, MsgType.MOUSE_EVENT, json.dumps(event).encode())
        except:
            pass

    def _on_mouse_move(self, event):
        now = time.time()
        # Limit send rate (~25 FPS)
        if now - self._last_move < 0.04:
            return

        x, y = self._map_coords(event.x, event.y)
        
        # Ignore tiny movements
        if self._last_pos is not None:
            lx, ly = self._last_pos
            if abs(x - lx) < 3 and abs(y - ly) < 3:
                return

        self._last_pos = (x, y)
        self._last_move = now
        
        self._send_mouse('move', x, y)

    def _get_button_name(self, num):
        if num == 1: return 'left'
        if num == 2: return 'middle'
        if num == 3: return 'right'
        return 'left'

    def _on_mouse_press(self, event):
        x, y = self._map_coords(event.x, event.y)
        self._send_mouse('click', x, y, button=self._get_button_name(event.num))
        
    def _on_mouse_double_click(self, event):
        x, y = self._map_coords(event.x, event.y)
        self._send_mouse('click', x, y, button='double')

    def _on_mouse_scroll(self, event):
        x, y = self._map_coords(event.x, event.y)
        dy = event.delta // 120
        self._send_mouse('scroll', x, y, dx=0, dy=dy)

    def _send_key(self, key_sym):
        if not self.running or not self.sock: return
        
        key = KEY_MAP.get(key_sym, key_sym.lower())
        if len(key) == 1 or key in SENDABLE:
            event = {'key': key}
            try:
                send_msg(self.sock, MsgType.KEY_EVENT, json.dumps(event).encode())
            except:
                pass

    def _on_key_press(self, event):
        self._send_key(event.keysym)

    def close(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.root.destroy()
