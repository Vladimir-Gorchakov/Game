import selectors
import socket
import types
import json
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class PlayerStatuses:
    all_players_info = dict()

    def __init__(self):
        pass

    def setInitialStatus(self, nickname: str):
        """New player creates in [0,0] position. Writes him in PlayerStatuses.all_players_info

        Args:
            nickname (str): Player nickname
        """
        initial_status = {
            "coords": [0, 0]
        }
        self.all_players_info[nickname] = initial_status

    def getStatuses(self):
        return {"players": self.all_players_info}

    def update_status(self, nickname: str, player_info: dict):
        """Updates PlayerStatuses.all_players_info

        Args:
            nickname (str): Player nickname
            player_info (dict): Dictionary like {"coords": [x, y], ...}
        """
        self.all_players_info[nickname] = player_info


class Server:
    connected_users = dict()
    statuses = PlayerStatuses()

    def __init__(self, server_ip: str = '127.0.0.1', server_port: int = 65432):
        # set sever ip:port
        # create selector and server socket
        self.sel = selectors.DefaultSelector()
        self.server_ip, self.server_port = server_ip, server_port
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # for nickname generation
        self.nickname_gen = self.nickname_generator()

    def get_connections(self):
        # Settings for server socket
        self.server_sock.bind((self.server_ip, self.server_port))
        self.server_sock.listen()
        logger.info(f"Server started on {self.server_ip}:{self.server_port}")
        self.server_sock.setblocking(False)
        self.sel.register(self.server_sock, selectors.EVENT_READ, data=None)

        try:
            # Main server loop
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_connection(key.fileobj)  # New connection
                    else:
                        self.handle_client(key, mask)  # Client sent data
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
            self.server_sock.close()
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            self.server_sock.close()
            self.sel.close()
        finally:
            self.sel.close()
            self.server_sock.close()

    def accept_connection(self, sock: socket.socket):
        # Register new client socket in server selector
        conn, addr = sock.accept()
        logger.info(f"Connected by {addr}")
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
        self.sel.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data=data)
        self.connected_users[conn.getpeername()] = next(self.nickname_gen)  # Dictionary like: client_socket -> nickname

    def handle_client(self, key: selectors.SelectorKey, mask: int):
        sock: socket = key.fileobj
        data: types.SimpleNamespace = key.data
        if mask & selectors.EVENT_READ:  # Client sent data
            recv_data = sock.recv(4096)
            if recv_data:
                logger.info(f"Received {recv_data} from {data.addr}")
                self.parse_recv(sock, recv_data, data)  # Parse recieved data
            else:  # Client closed the connection
                logger.info(f"Closing connection to {data.addr}")
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE and data.outb:  # If the server has a response
            logger.info(f"Sending {data.outb} to {data.addr}")
            sent = sock.send(data.outb)
            data.outb = data.outb[sent:]

    def parse_recv(self, conn: socket.socket, recv_data: bytes, data: types.SimpleNamespace):
        nickname = self.connected_users[conn.getpeername()]  # Get nickname by connection
        data_str = recv_data.decode("utf-8")
        # check message type
        match data_str:
            case "get_player_name":
                data.outb = nickname.encode("utf-8")  # Returns nickname for player
                return
            case "get_status":
                self.statuses.setInitialStatus(nickname)
                data.outb = self.encode_dict(self.statuses.getStatuses())  # Returns all players statuses
                return
            case _:
                data_dict = json.loads(data_str)  # Must be like {"coords": [x,y], ...}
                self.statuses.update_status(nickname=nickname, player_info=data_dict)
                data.outb = self.encode_dict(self.statuses.getStatuses())  # Returns all players statuses

    def nickname_generator(self):
        counter = 0
        while True:
            counter += 1
            yield f'player{counter}'

    def encode_dict(self, data: dict) -> bytes:
        return json.dumps(data).encode("utf-8")

    def decode_dict(self, data: bytes) -> dict:
        return json.loads(data.decode("utf-8"))


def main(args):
    server = Server(server_ip=args.ip, server_port=args.port)
    server.get_connections()



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str)
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    
    main(args)
