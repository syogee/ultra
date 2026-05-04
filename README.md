# Ultra Python Viewer

A modern, high-performance remote desktop application built in Python, featuring a centralized relay server and a premium CustomTkinter user interface.

## How to Connect 2 Different Laptops

By default, the application is set up to test locally on a single machine (`127.0.0.1`). To connect two different laptops over a network, follow these steps:

### 1. Set up the Relay Server
You need one machine to act as the "Relay Server" that both laptops can connect to.
- **Local Network (LAN):** If both laptops are on the same Wi-Fi, run `server.py` on one of the laptops (e.g., Laptop A). Find Laptop A's local IP address (e.g., `192.168.1.50`).
- **Over the Internet:** Run `server.py` on a cloud server (like a cheap VPS from DigitalOcean, AWS, or Linode) and note its public IP address. Make sure port `9999` is open on its firewall.

### 2. Update the Application Code
On both laptops, you need to point the application to the Relay Server's IP address.

1. Open `host.py` and change line 15:
   ```python
   RELAY_HOST = '192.168.1.50' # Replace with your Relay Server IP
   ```
2. Open `main.py` and change line 147 (in `_on_connect`):
   ```python
   # Replace the default '127.0.0.1' with your Relay Server IP
   viewer = ViewerWindow(partner_id, partner_pass, relay_host='192.168.1.50')
   ```
3. Update the footer text in `main.py` (line 167) so the UI accurately displays your Relay Server.

### 3. Run the App
Run `main.py` on both laptops. Share the ID and Password from Laptop A and enter it into Laptop B to control it remotely!

---

## How to Package the App & Start on Boot (Like Ultra Viewer)

To make your application behave like a real installed program (runs as an `.exe`, hides the terminal, and starts automatically when the computer turns on), you need to compile it and create an installer.

### Step 1: Compile to a single `.exe`
We will use **PyInstaller** to convert your Python scripts into a standalone executable.

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Run this command to compile `main.py` into a single file with no console window:
   ```bash
   pyinstaller --noconfirm --onedir --windowed --add-data "host.py;." --add-data "viewer.py;." --add-data "protocol.py;." --name "UltraViewer" main.py
   ```
   *(Note: Because your app relies on multiple modules, using `--onedir` instead of `--onefile` is safer and faster to launch).*
3. Your compiled app will be in the `dist\UltraViewer\` folder.

### Step 2: Create an Installer with Auto-Start
To make it install cleanly and start on system boot, use **Inno Setup** (a free installer builder for Windows).

1. Download and install [Inno Setup](https://jrsoftware.org/isinfo.php).
2. Open Inno Setup and create a new script using the Script Wizard.
3. Point the main executable to your `dist\UltraViewer\UltraViewer.exe` and include all other files in that `dist\UltraViewer\` folder.
4. **The Magic Step (Auto-Start):** To make the app start in the background when Windows boots, add this code to the `[Registry]` section of your Inno Setup Script:
   ```ini
   [Registry]
   Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "UltraPythonViewer"; ValueData: """{app}\UltraViewer.exe"""; Flags: uninsdeletevalue
   ```
5. Compile the script in Inno Setup. 

You now have a `setup.exe` file! When a user runs this, it will install the app to their Program Files and add a registry key. Every time they turn on their computer, `UltraViewer.exe` will start silently in the background, minimizing to the system tray thanks to your `pystray` code.
