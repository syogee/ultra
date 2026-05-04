import socket
import threading
import json
from protocol import recv_msg, send_msg, MsgType

HOST = "0.0.0.0"
PORT = 9999

hosts = {}
lock = threading.Lock()


def handle(client, addr):
    print("Connected:", addr)

    try:
        msg_type, data = recv_msg(client)

        if msg_type == MsgType.REGISTER_HOST:
            info = json.loads(data.decode())
            host_id = info["id"]
            password = info["password"]

            with lock:
                hosts[host_id] = {
                    "sock": client,
                    "password": password,
                    "viewer": None
                }

            print("Host:", host_id)

            while True:
                msg_type, payload = recv_msg(client)

                if msg_type is None:
                    break

                with lock:
                    viewer = hosts.get(host_id, {}).get("viewer")

                if viewer:
                    send_msg(viewer, msg_type, payload)

        elif msg_type == MsgType.REGISTER_VIEWER:
            info = json.loads(data.decode())
            host_id = info["id"]

            with lock:
                host = hosts.get(host_id)

            if not host:
                client.close()
                return

            host["viewer"] = client
            send_msg(client, MsgType.AUTH_RESP, b'OK')

            while True:
                msg_type, payload = recv_msg(client)

                if msg_type is None:
                    break

                with lock:
                    host_sock = hosts.get(host_id, {}).get("sock")

                if host_sock:
                    send_msg(host_sock, msg_type, payload)

    except:
        pass
    finally:
        client.close()


server = socket.socket()
server.bind((HOST, PORT))
server.listen()

print("Server running...")

while True:
    c, a = server.accept()
    threading.Thread(target=handle, args=(c, a), daemon=True).start()