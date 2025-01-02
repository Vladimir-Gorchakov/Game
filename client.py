import socket
import json
import pygame

import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)



class client:
    def __init__(self, SERVER_IP: str, SERVER_PORT: int):
        self.server_socket = self.connect_to_server(SERVER_IP, SERVER_PORT)
        if self.server_socket is None:
            raise Exception("Failed to create a socket connection")

    def connect_to_server(self, SERVER_IP: str, SERVER_PORT: int) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((SERVER_IP, SERVER_PORT))
            logger.info(f"Connected to server at {SERVER_IP}:{SERVER_PORT}")
            return s
        except ConnectionRefusedError:
            logger.error("Connection refused. Is the server running?")
            return None
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None

    def receive_json(self) -> dict:
        try:
            data = self.server_socket.recv(4096)
            if not data:
                return None  # Server closed the connection
            json_data = json.loads(data.decode('utf-8'))
            return json_data
        except Exception as e:
            logger.error(f"Error receiving JSON data: {e}, {traceback.format_exc()}")
            return None

    def send_json(self, data: dict):
        try:
            json_data = json.dumps(data).encode("utf-8")
            self.server_socket.sendall(json_data)
        except Exception as e:
            logger.error(f"Error sending JSON data: {e}, {traceback.format_exc()}")
    
    def close(self):
        try:
            self.server_socket.close()
            logger.info("Socket closed successfully")
        except Exception as e:
             logger.error(f"Error closing socket: {e}, {traceback.format_exc()}")


class game:
    def __init__(self, SERVER_IP: str, SERVER_PORT: int):
        # Constants
        self.FPS = 30
        self.PLAYER_RADIUS = 20
        self.MOVE_SPEED = 10
        self.WINDOW_WIDTH = 1200
        self.WINDOW_HEIGHT = 800
        self.PLAYER_COLOR = None # example: (0, 0, 255)
        
        # get server socket from client class
        self.client = client(SERVER_IP, SERVER_PORT)
        self.server_socket = self.client.server_socket

        # Needed for pygame
        pygame.init()
        self.clock = pygame.time.Clock()
        self.window = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        self.running = True

        # player info
        self.player_name = None # player1 or player2
        self.status = None # {"players" : {player1 : {coords: [x, y], ...}, player2 : {...}}}
        self.player_info = None # {coords: [x, y], ...} or self.status["players"][self.player_name]


    def start_game(self):
        # autorization
        self.autorization()

        # starting game
        self.game_loop()
        

    def autorization(self):
        # get player name
        self.server_socket.sendall("get_player_name".encode("utf-8"))
        self.player_name = self.server_socket.recv(1024).decode("utf-8") # excpect to get player1 or player2
        assert "player" in self.player_name, f"Player name is wrong, got {self.player_name}"

        # get current status of the game
        self.server_socket.sendall("get_status".encode("utf-8"))
        self.update_status() # excpect {"players" : {player1 : {coords: [x, y], ...}, player2 : {...}}}
        assert isinstance(self.status, dict)
        assert self.status


    def game_loop(self):
        while self.running:
            # display current status on screen
            self.render_data()

            # check player action and do and update player info
            self.parse_events_and_do_actions()

            # send info about new player status
            self.client.send_json(self.player_info)

            # get info about game from server and save it
            self.update_status()

            # Limit the FPS by sleeping for the remainder of the frame time
            self.clock.tick(self.FPS)


    def parse_events_and_do_actions(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # If button is presed check what are pressed
            if event.type == pygame.KEYDOWN: 
                match event.key:
                    case pygame.K_w:
                        self.player_info["coords"][1] += 10
                    case pygame.K_s:
                        self.player_info["coords"][1] -= 10
                    case pygame.K_d:
                        self.player_info["coords"][0] += 10
                    case pygame.K_a:
                        self.player_info["coords"][0] -= 10
                    case _:
                        pass         


    def render_data(self):
        self.window.fill((0, 0, 0))

        players_info = self.status["players"]
        for player_name in players_info.keys():
            pygame.draw.circle(surface = self.window, 
                            color=(0, 0, 255),
                            center=players_info[player_name]["coords"],
                            radius=20)
        
        pygame.display.flip()


    def update_status(self):
        self.status = self.client.receive_json()
        self.player_info = self.status["players"][self.player_name]


def main(SERVER_IP, SERVER_PORT):
    try:
        GAME = game(SERVER_IP, SERVER_PORT)
        GAME.start_game()
    except Exception as e:
        GAME.client.close()
        raise e
    finally:
        GAME.client.close()



if __name__ == "__main__":
    SERVER_IP = "127.0.0.1"
    SERVER_PORT = 65432

    main(SERVER_IP, SERVER_PORT)