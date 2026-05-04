import json
import os
import time
import random
from host import HostService

CONFIG_FILE = os.path.join(os.path.expanduser("~"), "ultra_viewer_config.json")

def load_or_create_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            
    # Generate new config if missing or corrupted
    raw_id = str(random.randint(10_000_000, 99_999_999))
    my_id = f"{raw_id[:2]} {raw_id[2:5]} {raw_id[5:]}" # "XX XXX XXX"
    my_password = str(random.randint(10000, 99999))
    
    config = {
        "host_id": my_id,
        "password": my_password,
        "relay_host": "127.0.0.1"
    }
    
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving config: {e}")
        
    return config

def main():
    config = load_or_create_config()
    host_id = config.get("host_id")
    password = config.get("password")
    relay_host = config.get("relay_host", "127.0.0.1")
    
    print(f"Starting UltraViewerService...")
    print(f"ID: {host_id}")
    print(f"Relay: {relay_host}")
    
    service = HostService(host_id, password, relay_host=relay_host)
    service.start()
    
    # Keep the main thread alive since HostService runs in a daemon thread
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping service...")
        service.stop()

if __name__ == "__main__":
    main()
