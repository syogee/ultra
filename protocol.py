import struct
import json

class MsgType:
    REGISTER_HOST = 1
    REGISTER_VIEWER = 2
    AUTH_RESP = 3
    SCREEN_FRAME = 4
    MOUSE_EVENT = 5
    KEY_EVENT = 6
    DISCONNECT = 7

def send_msg(sock, msg_type, data_bytes=b''):
    """Sends a message with a 4-byte length prefix, 1-byte type, and payload."""
    payload = struct.pack('!B', msg_type) + data_bytes
    msg = struct.pack('!I', len(payload)) + payload
    sock.sendall(msg)

def recv_msg(sock):
    """Receives a length-prefixed message and returns (msg_type, data_bytes)."""
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None, None
    msglen = struct.unpack('!I', raw_msglen)[0]
    data = recvall(sock, msglen)
    if not data:
        return None, None
    msg_type = struct.unpack('!B', data[:1])[0]
    return msg_type, data[1:]

def recvall(sock, n):
    """Helper function to recv n bytes or return None if EOF is hit"""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)
