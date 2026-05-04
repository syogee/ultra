import socket
import threading
import json
import time
import struct
import io

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
        
        self.quality = 65
        self.resize_factor = 0.75
        self.fps_cap = 20
        self.last_x = None
        self.last_y = None
            
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
                
    def _run(self):
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.relay_host, self.relay_port))
                
                # Register host
                reg_info = {'id': self.host_id, 'password': self.password}
                send_msg(self.sock, MsgType.REGISTER_HOST, json.dumps(reg_info).encode())
                
                print(f"[Host] Registered to Relay Server as {self.host_id}")
                
                # Start screen capture thread
                capture_thread = threading.Thread(target=self._capture_screen)
                capture_thread.daemon = True
                capture_thread.start()
                
                # Listen for inputs
                self._listen_for_events()
                
            except Exception as e:
                print(f"[Host] Connection error: {e}")
                time.sleep(3) # Wait before reconnecting
            finally:
                if self.sock:
                    self.sock.close()

    def _capture_screen(self):
        with mss.mss() as sct:
            mon = sct.monitors[1]
            # Send original screen size to viewer first so it can map coordinates properly
            # In our protocol, the SCREEN_FRAME header sends width/height
            
            while self.running and self.sock:
                t0 = time.time()
                try:
                    img = sct.grab(mon)
                    pil = Image.frombytes('RGB', (img.width, img.height), img.rgb)
                    nw = int(img.width * self.resize_factor)
                    nh = int(img.height * self.resize_factor)
                    pil = pil.resize((nw, nh), Image.LANCZOS)
                    
                    buf = io.BytesIO()
                    pil.save(buf, format='JPEG', quality=self.quality)
                    data = buf.getvalue()
                    
                    # Prepend original width and height
                    header = struct.pack('!HH', img.width, img.height)
                    send_msg(self.sock, MsgType.SCREEN_FRAME, header + data)
                    
                except Exception as e:
                    print(f"[Host] Capture error: {e}")
                    break
                    
                elapsed = time.time() - t0
                time.sleep(max(0, (1.0 / self.fps_cap) - elapsed))

    def _listen_for_events(self):
        while self.running and self.sock:
            msg_type, payload = recv_msg(self.sock)
            if msg_type is None or msg_type == MsgType.DISCONNECT:
                print("[Host] Disconnected from Relay Server or Viewer")
                break
                
            if msg_type == MsgType.MOUSE_EVENT:
                event = json.loads(payload.decode('utf-8'))
                action = event['action']
                
                if action == 'move':
                    tx, ty = event['x'], event['y']
                    # Ignore tiny jitter
                    if self.last_x is not None:
                        if abs(tx - self.last_x) < 2 and abs(ty - self.last_y) < 2:
                            continue
                    pyautogui.moveTo(tx, ty, _pause=False)
                    self.last_x, self.last_y = tx, ty
                    
                elif action == 'click':
                    btn = event.get('button', 'left')
                    if btn == 'left':
                        pyautogui.click(event['x'], event['y'], _pause=False)
                    elif btn == 'right':
                        pyautogui.rightClick(event['x'], event['y'], _pause=False)
                    elif btn == 'double':
                        pyautogui.doubleClick(event['x'], event['y'], _pause=False)
                        
                elif action == 'scroll':
                    # pyautogui.scroll takes (clicks, x, y)
                    pyautogui.scroll(event['dy'], event['x'], event['y'], _pause=False)
                    
            elif msg_type == MsgType.KEY_EVENT:
                event = json.loads(payload.decode('utf-8'))
                key = event['key']
                pyautogui.press(key, _pause=False)
