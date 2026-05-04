import socket
import threading
import json
from protocol import recv_msg, send_msg, MsgType

HOST = '0.0.0.0'
PORT = 9999

# Dictionary to store connected hosts: {host_id: {'password': password, 'sock': sock, 'viewer_sock': None}}
hosts = {}
hosts_lock = threading.Lock()

def handle_client(client_sock, addr):
    print(f"[+] New connection from {addr}")
    
    # Wait for registration message
    msg_type, data = recv_msg(client_sock)
    if msg_type is None:
        client_sock.close()
        return

    if msg_type == MsgType.REGISTER_HOST:
        info = json.loads(data.decode('utf-8'))
        host_id = info['id']
        password = info['password']
        
        with hosts_lock:
            hosts[host_id] = {'password': password, 'sock': client_sock, 'viewer_sock': None}
        
        print(f"[*] Host registered: {host_id}")
        
        # Wait for viewer to connect and data to be relayed
        try:
            while True:
                msg_type, payload = recv_msg(client_sock)
                if msg_type is None:
                    break
                
                with hosts_lock:
                    viewer_sock = hosts[host_id].get('viewer_sock')
                
                if viewer_sock:
                    try:
                        send_msg(viewer_sock, msg_type, payload)
                    except Exception as e:
                        print(f"Error sending to viewer: {e}")
        finally:
            with hosts_lock:
                if host_id in hosts:
                    viewer_sock = hosts[host_id].get('viewer_sock')
                    if viewer_sock:
                        try:
                            send_msg(viewer_sock, MsgType.DISCONNECT)
                        except:
                            pass
                    del hosts[host_id]
            client_sock.close()
            print(f"[-] Host disconnected: {host_id}")

    elif msg_type == MsgType.REGISTER_VIEWER:
        info = json.loads(data.decode('utf-8'))
        target_id = info['id']
        password = info['password']
        
        with hosts_lock:
            host = hosts.get(target_id)
            if host and str(host['password']) == password:
                if host['viewer_sock'] is not None:
                    send_msg(client_sock, MsgType.AUTH_RESP, json.dumps({'status': 'error', 'msg': 'Host already has a viewer'}).encode())
                    client_sock.close()
                    return
                
                host['viewer_sock'] = client_sock
                send_msg(client_sock, MsgType.AUTH_RESP, json.dumps({'status': 'ok'}).encode())
                print(f"[*] Viewer connected to host: {target_id}")
            else:
                send_msg(client_sock, MsgType.AUTH_RESP, json.dumps({'status': 'error', 'msg': 'Invalid ID or Password'}).encode())
                client_sock.close()
                return
        
        # Relay viewer inputs to host
        try:
            while True:
                msg_type, payload = recv_msg(client_sock)
                if msg_type is None:
                    break
                
                with hosts_lock:
                    host_sock = hosts.get(target_id, {}).get('sock')
                
                if host_sock:
                    try:
                        send_msg(host_sock, msg_type, payload)
                    except Exception as e:
                        print(f"Error sending to host: {e}")
                        break
        finally:
            with hosts_lock:
                if target_id in hosts and hosts[target_id]['viewer_sock'] == client_sock:
                    hosts[target_id]['viewer_sock'] = None
            client_sock.close()
            print(f"[-] Viewer disconnected from host: {target_id}")

    else:
        print(f"[-] Unknown registration type: {msg_type}")
        client_sock.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(10)
    print(f"[*] Relay server listening on {HOST}:{PORT}")
    
    while True:
        client_sock, addr = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_sock, addr))
        client_thread.daemon = True
        client_thread.start()

if __name__ == "__main__":
    main()
