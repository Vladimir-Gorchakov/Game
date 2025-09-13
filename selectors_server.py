import selectors
import socket
import string
import types
import json

class PlayerStatuses:
    all_players_info = dict()
    
    def __init__(self):
        pass

    def setInitialStatus(self, nickname: str):
        initial_status = {
            "coords": [0, 0]
        }
        self.all_players_info[nickname] = initial_status

    def getStatuses(self):
        return self.all_players_info

    def update_status(self, nickname: str, player_info: dict):
        """
        Returns {"players" : {player1 : {coords: [x, y], ...}, player2 : {...}}}

        Args:
            nickname (str): player nickname
            player_info (dict): {coords: [x, y], ...}
        """
        self.all_players_info[nickname] = player_info
    



class Server:
    connected_users = dict()
    statuses = PlayerStatuses()

    def __init__(self, server_ip: str = '127.0.0.1', server_port: int = 65432):
        self.sel = selectors.DefaultSelector()
        self.server_ip, self.server_port = server_ip, server_port
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.nickname_gen = self.nickname_generator()
    
    def get_connections(self):
        self.server_sock.bind((self.server_ip, self.server_port))
        self.server_sock.listen()
        print(f"Server started on {self.server_ip}:{self.server_port}")
        self.server_sock.setblocking(False)
        self.sel.register(self.server_sock, selectors.EVENT_READ, data=None)

        try:
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_connection(key.fileobj)  
                    else:
                        self.handle_client(key, mask)  
        except KeyboardInterrupt:
            print("Server shutting down...")
            self.server_sock.close()
        finally:
            self.sel.close()
            self.server_sock.close()

    def accept_connection(self, sock: socket.socket):
        conn, addr = sock.accept()
        print(f"Connected by {addr}")
        conn.setblocking(False)  
        data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
        self.sel.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data=data)
        self.connected_users[conn.getpeername()] = next(self.nickname_gen)

    def handle_client(self, key: selectors.SelectorKey, mask: int):
        sock: socket = key.fileobj
        data: types.SimpleNamespace = key.data
        if mask & selectors.EVENT_READ:  
            recv_data = sock.recv(1024)  
            if recv_data:
                print(f"Received {recv_data} from {data.addr}")
                self.parse_recv(sock, recv_data, data)
            else:
                print(f"Closing connection to {data.addr}")
                self.sel.unregister(sock)  
                sock.close()
        if mask & selectors.EVENT_WRITE and data.outb:  
            print(f"Sending {data.outb} to {data.addr}")
            sent = sock.send(data.outb)
            data.outb = data.outb[sent:]
    
    def parse_recv(self, conn: socket.socket, recv_data: bytes, data: types.SimpleNamespace):
        nickname = self.connected_users[conn.getpeername()]
        data_str = recv_data.decode("utf-8")
        match data_str:
            # TODO при первом подключении должно быть get_player_name 
            case "get_player_name":
                data.outb = nickname.encode("utf-8")
                return
            case "get_status":
                self.statuses.setInitialStatus(nickname)
                data.outb = self.encode_dict(self.statuses.getStatuses())
                return
            case _:
                # else {coords: [x, y], ...}
                data_dict = json.loads(data_str)
                self.statuses.update_status(nickname=nickname, player_info=data_dict)
                data.outb = self.encode_dict(self.statuses.getStatuses())
               
    def nickname_generator(self):
        counter = 0
        while True:
            counter += 1
            yield f'player{counter}'
            
    def encode_dict(self, data: dict) -> bytes:
        return json.dumps(data).encode("utf-8")

    def decode_dict(self, data: bytes) -> dict:
        return json.loads(data.decode("utf-8"))
    
            

def main():
    server = Server(server_ip="127.0.0.1", server_port=65432)
    server.get_connections()

if __name__ == '__main__':
    main()