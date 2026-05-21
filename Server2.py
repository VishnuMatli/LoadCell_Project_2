import os
import socket
import struct

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000
SHARE_FOLDER = "./adc_data"

def get_file_list():
    files = [f for f in os.listdir(SHARE_FOLDER) if os.path.isfile(os.path.join(SHARE_FOLDER, f))]
    return files

def send_file_by_index(client, index, files):
    if index < 0 or index >= len(files):
        # Send zero filename length (end signal)
        client.sendall(struct.pack(">I", 0))
        return False

    filename = files[index]
    filepath = os.path.join(SHARE_FOLDER, filename)
    file_size = os.path.getsize(filepath)

    # Send filename length + filename
    client.sendall(struct.pack(">I", len(filename)))
    client.sendall(filename.encode())

    # Send file size
    client.sendall(struct.pack(">Q", file_size))

    # Send file content
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            client.sendall(chunk)

    print(f"[SERVER] Sent file {index}: '{filename}' ({file_size} bytes)")
    return True

def start_server():
    files = get_file_list()
    print(f"[SERVER] {len(files)} files available.")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER_IP, SERVER_PORT))
    server.listen(1)
    print(f"[SERVER] Listening on {SERVER_IP}:{SERVER_PORT}")

    client, addr = server.accept()
    print(f"[SERVER] Connection from {addr}")

    while True:
        # Receive 4-byte index
        data = client.recv(4)
        if not data:
            break
        index = struct.unpack(">I", data)[0]
        if not send_file_by_index(client, index, files):
            break

    print("[SERVER] Transmission complete")
    client.close()
    server.close()

if __name__ == "__main__":
    os.makedirs(SHARE_FOLDER, exist_ok=True)
    start_server()
