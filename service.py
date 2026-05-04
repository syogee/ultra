import json
import os
import time
import random
from host import HostService

CONFIG_FILE = os.path.join(os.path.expanduser("~"), r"\Desktop\ultra\config.json")

def load_or_create_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            
    # Generate new config if missing or corrupted
    raw_id = str(random.randint(100000000, 999999999))
    my_id = f"{raw_id[:3]}{raw_id[3:6]}{raw_id[6:]}" # no spaces
    my_password = str(random.randint(1000, 9999))
    
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
