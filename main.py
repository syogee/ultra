import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import socket
import random
import threading
import pystray
from PIL import Image
import json
import os

from host import HostService
from viewer import ViewerWindow

# ── Colour palette ──
PRIMARY   = "#6C63FF"
PRIMARY_H = "#5A52E0"   
SUCCESS   = "#2ECC71"
DANGER    = "#E74C3C"
SURFACE   = "#1E1E2E"
CARD      = "#2A2A3C"
CARD_L    = "#33334A"
TEXT      = "#E0E0F0"
TEXT_DIM  = "#9090B0"
ACCENT_BG = "#3A3A5C"
FIELD_BG  = "#22223A"

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"relay_host": "127.0.0.1"}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
    except:
        pass

def get_local_ips():
    ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and ip != "127.0.0.1":
                ips.append(ip)
    except Exception:
        pass
    if not ips:
        ips.append("127.0.0.1")
    return ips

class UltraApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.config = load_config()
        self.relay_host = self.config.get("relay_host", "127.0.0.1")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.title("⚡ Ultra Python Viewer")
        self.geometry("760x580")
        self.resizable(False, False)
        self.configure(fg_color=SURFACE)
        
        # Generate credentials
        raw_id = str(random.randint(100000000, 999999999))
        self.my_id = f"{raw_id[:3]} {raw_id[3:6]} {raw_id[6:]}"
        self.my_password = str(random.randint(1000, 9999))
        self.local_ips = get_local_ips()
        
        self.host_service = None
        
        self._build_ui()
        
        # Start Host Service Automatically
        self._on_start()
        
        # System Tray setup
        self.protocol('WM_DELETE_WINDOW', self.hide_window)
        img = Image.new('RGB', (64, 64), color=(0, 120, 215))
        menu = (pystray.MenuItem('Show', self.show_window), pystray.MenuItem('Exit', self.quit_app))
        self.tray_icon = pystray.Icon("name", img, "Ultra Python Viewer", menu)

    def _build_ui(self):
        # ── Header strip ──
        header = ctk.CTkFrame(self, fg_color=CARD, height=50, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="⚡  Ultra Python Viewer",
                     font=ctk.CTkFont("Segoe UI", 16, "bold"),
                     text_color=TEXT).pack(side="left", padx=20)
        self.header_status = ctk.CTkLabel(
            header, text="● Offline", text_color=DANGER,
            font=ctk.CTkFont("Segoe UI", 12))
        self.header_status.pack(side="right", padx=20)

        # ── Main container ──
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=16, pady=16)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # ── LEFT CARD: Allow Remote Control ──
        left = ctk.CTkFrame(container, fg_color=CARD, corner_radius=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(left, text="Allow Remote Control",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=20, pady=(20, 12))

        sep = ctk.CTkFrame(left, fg_color=ACCENT_BG, height=1)
        sep.pack(fill="x", padx=20)

        inner_left = ctk.CTkFrame(left, fg_color="transparent")
        inner_left.pack(fill="both", expand=True, padx=20, pady=12)

        self._info_row(inner_left, "🆔  Your ID", self.my_id.replace(" ", ""))
        self._status_dots(inner_left)
        self._info_row(inner_left, "🔒  Password", self.my_password)
        
        ip_text = "  ~  ".join(self.local_ips)
        self._info_row(inner_left, "🌐  Your IP", ip_text)

        self.status_var = ctk.StringVar(value="Stopped")
        ctk.CTkLabel(inner_left, textvariable=self.status_var,
                     text_color=TEXT_DIM,
                     font=ctk.CTkFont("Segoe UI", 11)).pack(pady=(12, 4))

        btn_row = ctk.CTkFrame(inner_left, fg_color="transparent", height=48)
        btn_row.pack(fill="x", pady=(10, 0))
        btn_row.pack_propagate(False)
        self.btn_start = ctk.CTkButton(
            btn_row, text="▶  Start", width=130, height=42,
            fg_color=SUCCESS, hover_color="#27AE60",
            text_color="#fff", font=ctk.CTkFont("Segoe UI", 13, "bold"),
            corner_radius=10, command=self._on_start)
        self.btn_start.pack(side="left", expand=True, fill="both", padx=(0, 6))

        self.btn_stop = ctk.CTkButton(
            btn_row, text="■  Stop", width=130, height=42,
            fg_color=DANGER, hover_color="#C0392B",
            text_color="#fff", font=ctk.CTkFont("Segoe UI", 13, "bold"),
            corner_radius=10, state="disabled", command=self._on_stop)
        self.btn_stop.pack(side="left", expand=True, fill="both", padx=(6, 0))

        # ── RIGHT CARD: Control Remote Computer ──
        right = ctk.CTkFrame(container, fg_color=CARD, corner_radius=16)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(right, text="Control Remote Computer",
                     font=ctk.CTkFont("Segoe UI", 14, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=20, pady=(20, 12))

        sep2 = ctk.CTkFrame(right, fg_color=ACCENT_BG, height=1)
        sep2.pack(fill="x", padx=20)

        inner_right = ctk.CTkFrame(right, fg_color="transparent")
        inner_right.pack(fill="both", expand=True, padx=20, pady=12)

        ctk.CTkLabel(inner_right, text="Partner ID",
                     text_color=TEXT_DIM,
                     font=ctk.CTkFont("Segoe UI", 11)).pack(anchor="w", pady=(4, 4))
        self.ent_ip = ctk.CTkEntry(
            inner_right, height=38, corner_radius=10,
            fg_color=FIELD_BG, border_color=ACCENT_BG,
            text_color=TEXT, placeholder_text="e.g. 123456789",
            font=ctk.CTkFont("Consolas", 13))
        self.ent_ip.pack(fill="x")

        ctk.CTkLabel(inner_right, text="Password",
                     text_color=TEXT_DIM,
                     font=ctk.CTkFont("Segoe UI", 11)).pack(anchor="w", pady=(12, 4))
        self.ent_pass = ctk.CTkEntry(
            inner_right, height=38, corner_radius=10,
            fg_color=FIELD_BG, border_color=ACCENT_BG,
            text_color=TEXT, show="•", placeholder_text="Enter password",
            font=ctk.CTkFont("Consolas", 13))
        self.ent_pass.pack(fill="x")

        # View only
        self.view_only_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(inner_right, text="View only",
                        variable=self.view_only_var,
                        text_color=TEXT, fg_color=PRIMARY,
                        hover_color=PRIMARY_H, corner_radius=6,
                        font=ctk.CTkFont("Segoe UI", 12)).pack(anchor="w", pady=(20, 6))

        connect_wrap = ctk.CTkFrame(inner_right, fg_color="transparent", height=50)
        connect_wrap.pack(fill="x", pady=(20, 0))
        connect_wrap.pack_propagate(False)
        self.btn_connect = ctk.CTkButton(
            connect_wrap, text="🔗  Connect", height=46,
            fg_color=PRIMARY, hover_color=PRIMARY_H,
            text_color="#fff", font=ctk.CTkFont("Segoe UI", 14, "bold"),
            corner_radius=12, command=self._on_connect)
        self.btn_connect.pack(fill="both", expand=True)

        # ── Footer ──
        footer = ctk.CTkFrame(self, fg_color=CARD, height=40, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        
        ctk.CTkLabel(footer, text="Relay IP:", text_color=TEXT_DIM, font=ctk.CTkFont("Segoe UI", 11)).pack(side="left", padx=(20, 5), pady=10)
        
        self.ent_relay_ip = ctk.CTkEntry(footer, width=120, height=28, fg_color=FIELD_BG, border_color=ACCENT_BG, text_color=TEXT, font=ctk.CTkFont("Consolas", 11))
        self.ent_relay_ip.insert(0, self.relay_host)
        self.ent_relay_ip.pack(side="left", pady=6)
        
        btn_save_relay = ctk.CTkButton(footer, text="Save & Apply", width=100, height=28, fg_color=ACCENT_BG, hover_color=PRIMARY, font=ctk.CTkFont("Segoe UI", 11), command=self._save_relay_ip)
        btn_save_relay.pack(side="left", padx=10, pady=6)

    def _save_relay_ip(self):
        new_ip = self.ent_relay_ip.get().strip()
        if new_ip:
            self.relay_host = new_ip
            self.config["relay_host"] = new_ip
            save_config(self.config)
            messagebox.showinfo("Saved", f"Relay IP updated to {new_ip}.\nRestarting Host Service...")
            self._on_stop()
            self._on_start()

    def _info_row(self, parent, label, value):
        ctk.CTkLabel(parent, text=label, text_color=TEXT_DIM,
                     font=ctk.CTkFont("Segoe UI", 11)).pack(anchor="w", pady=(8, 2))
        field = ctk.CTkFrame(parent, fg_color=FIELD_BG, corner_radius=10, height=36)
        field.pack(fill="x")
        field.pack_propagate(False)
        ctk.CTkLabel(field, text=value, text_color="#A5B4FC",
                     font=ctk.CTkFont("Consolas", 14, "bold")).pack(
                         side="left", padx=14, pady=6)

    def _status_dots(self, parent):
        dot_frame = ctk.CTkFrame(parent, fg_color="transparent", height=16)
        dot_frame.pack(anchor="e", pady=2)
        colours = [SUCCESS]*3 + [TEXT_DIM]*3
        for c in colours:
            d = tk.Canvas(dot_frame, width=10, height=10, bg=CARD, highlightthickness=0)
            d.pack(side="left", padx=2)
            d.create_oval(1, 1, 9, 9, fill=c, outline=c)

    def _on_start(self):
        if not self.host_service:
            # remove spaces from ID before starting
            self.host_service = HostService(self.my_id.replace(" ", ""), self.my_password, relay_host=self.relay_host)
            self.host_service.start()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.header_status.configure(text="● Online", text_color=SUCCESS)
        self.status_var.set("Service Running")

    def _on_stop(self):
        if self.host_service:
            self.host_service.stop()
            self.host_service = None
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.header_status.configure(text="● Offline", text_color=DANGER)
        self.status_var.set("Service Stopped")

    def _on_connect(self):
        partner_id = self.ent_ip.get().strip().replace(" ", "")
        partner_pass = self.ent_pass.get().strip()
        
        if not partner_id or not partner_pass:
            messagebox.showwarning("Input required", "Enter the Partner ID and Password.")
            return

        print(f"Connecting to {partner_id} via {self.relay_host}...")
        
        # Start viewer window
        viewer = ViewerWindow(partner_id, partner_pass, relay_host=self.relay_host)
        
        # If view only is checked, unbind mouse and keyboard events
        if self.view_only_var.get():
            viewer.canvas.unbind("<Motion>")
            viewer.canvas.unbind("<ButtonPress>")
            viewer.canvas.unbind("<Double-Button-1>")
            viewer.canvas.unbind("<MouseWheel>")
            viewer.root.unbind("<Key>")
            
        viewer.start()

    def hide_window(self):
        self.withdraw()
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon=None, item=None):
        if icon:
            icon.stop()
        self.after(0, self.deiconify)

    def quit_app(self, icon=None, item=None):
        if icon:
            icon.stop()
        if self.host_service:
            self.host_service.stop()
        self.quit()

if __name__ == "__main__":
    app = UltraApp()
    app.mainloop()
