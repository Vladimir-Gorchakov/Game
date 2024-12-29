import socket
import threading
#import logging

HOST = '127.0.0.2'  # Standard loopback interface address (localhost)
PORT = 65432      # Port to listen on (non-privileged ports are > 1023)

def handle_client(conn, addr):
    """Handles communication with a single client."""
    print(f"Connected by {addr}")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                print("cycle braked")
                break
            decoded_data = data.decode()
            print(f"Received from {addr}: {decoded_data}")
            # Echo the data back to the client
            conn.sendall(data)
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        print(f"Connection with {addr} closed.")
        conn.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            # Create a new thread to handle the client
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()


if __name__ == "__main__":
    main()