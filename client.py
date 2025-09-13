import socket
import json
import pygame
from pathlib import Path

import logging
import traceback
import argparse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class client:
    def __init__(self, SERVER_IP: str, SERVER_PORT: int, RECV_SIZE: int = 1024):
        self.RECV_SIZE = RECV_SIZE
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
            data = self.server_socket.recv(self.RECV_SIZE)
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
        self.PLAYER_COLOR = None  # example: (0, 0, 255)

        # get server socket from client class
        self.client = client(SERVER_IP, SERVER_PORT)
        self.server_socket = self.client.server_socket

        # Needed for pygame
        pygame.init()
        pygame.font.init()  # for text rendering
        self.font = pygame.font.SysFont('arial', 16)  # set text type and size
        self.clock = pygame.time.Clock()
        self.window = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        self.running = True

        # Game status
        self.status: dict = None  # {"players" : {player1 : {coords: [x, y], ...}, player2 : {...}}}
        self.player: player = None  # will be defined during autorization

        # Get the path to the directory of the script
        self.script_dir = Path(__file__).resolve().parent

    def start_game(self):
        # autorization
        self.autorization()

        # starting game
        self.game_loop()

    def autorization(self):
        # get player name
        self.server_socket.sendall("get_player_name".encode("utf-8"))
        player_name = self.server_socket.recv(self.client.RECV_SIZE).decode("utf-8")  # excpect to get player(num)
        assert "player" in player_name, f"Player name is wrong, got {self.player_name}"

        # init player and set sking by player name
        self.player = player(player_name)
        self.player.set_skin(self.script_dir)

        # get current status of the game
        self.server_socket.sendall("get_status".encode("utf-8"))
        self.update_status()  # excpect {"players" : {player1 : {coords: [x, y], ...}, player2 : {...}}}
        assert isinstance(self.status, dict)
        assert self.status

    def game_loop(self):
        while self.running:
            # display current status on screen
            self.render_data()

            # check player action and do and update player info
            self.parse_events()
            self.player.do_action(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

            # send info about new player status
            self.client.send_json(self.player.get_data_as_dict())

            # get info about game from server and save it
            self.update_status()

            # Limit the FPS by sleeping for the remainder of the frame time
            self.clock.tick(self.FPS)

    def parse_events(self):
        for event in pygame.event.get():
            # if button close is pressed on window end game
            if event.type == pygame.QUIT:
                self.running = False

            # if window was resized, write new size
            if event.type == pygame.VIDEORESIZE:
                self.WINDOW_WIDTH, self.WINDOW_HEIGHT = event.w, event.h

            # If button is presed check what are pressed
            if event.type == pygame.KEYDOWN:
                match event.key:
                    case pygame.K_w:
                        self.player.K_w_pressed = True
                    case pygame.K_s:
                        self.player.K_s_pressed = True
                    case pygame.K_d:
                        self.player.K_d_pressed = True
                    case pygame.K_a:
                        self.player.K_a_pressed = True
                    case _:
                        pass

            if event.type == pygame.KEYUP:
                match event.key:
                    case pygame.K_w:
                        self.player.K_w_pressed = False
                    case pygame.K_s:
                        self.player.K_s_pressed = False
                    case pygame.K_d:
                        self.player.K_d_pressed = False
                    case pygame.K_a:
                        self.player.K_a_pressed = False

    def render_data(self):
        self.window.fill((0, 0, 0))

        players_info = self.status["players"]
        for player_name in players_info.keys():
            x, y = players_info[player_name]["coords"]

            if player_name == self.player.player_name:
                # draw self.player on screen center
                self.window.blit(self.player.resized_skin , (self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2))
            else:
                # draw other players relatively to self.player
                self.window.blit(self.player.resized_skin , (x - self.player.pos[0], y - self.player.pos[1]))

        # xm, ym = pygame.mouse.get_pos()
        # x, y = self.player.pos
        # x, y = int(x), int(y)
        # text1 = self.font.render(f"player coords = {x, y}", False, (0, 180, 0))
        # text2 = self.font.render(f"mouse coords = {xm, ym}", False, (0, 180, 0))
        # text1.get_rect().bottomright

        # self.window.blit(text1, (2 * self.WINDOW_WIDTH // 3, 2 * self.WINDOW_HEIGHT // 3))
        # self.window.blit(text2, (2 * self.WINDOW_WIDTH // 3, 2 * self.WINDOW_HEIGHT // 3 + 100))

        pygame.display.flip()

    def update_status(self):
        self.status = self.client.receive_json()
        self.player.set_player_info(self.status)


class player:
    "Contain player info like position, skill cooldown, what button are pressed and so on"
    def __init__(self, player_name: str):
        # player info
        self.player_name = player_name  # player1 or player2 ...
        self.player_info = None
        self.pos = None
        self.speed = 10
        self.skin = None

        # Keyboard status
        self.K_w_pressed = False
        self.K_s_pressed = False
        self.K_a_pressed = False
        self.K_d_pressed = False

    def get_data_as_dict(self):
        self.player_info["coords"] = self.pos
        # self.player_info["speed"] = self.speed  # is it really needed?
        # logger.debug(f"self.player_info = {self.player_info}")
        return self.player_info

    def set_player_info(self, player_info: dict):
        player_info = player_info["players"][self.player_name]
        self.player_info = player_info  # {coords: [x, y], ...} or self.status["players"][self.player_name]
        self.pos = player_info["coords"]
        # self.speed = player_info["speed"]

    def set_skin(self, script_dir: Path):
        self.skin = pygame.image.load(script_dir / "skin" / "player1.png")
        self.resized_skin = pygame.transform.scale(self.skin, (20, 20))

    def do_action(self, WINDOW_WIDTH: int, WINDOW_HEIGHT: int):
        # get player and mouse position
        xm, ym = pygame.mouse.get_pos()
        dx, dy = xm - WINDOW_WIDTH // 2 , ym - WINDOW_HEIGHT // 2
        if dx == 0 and dy == 0:
            return

        # compute moving direction, norm(dirction) = 1
        l2_norm = (dx**2 + dy**2)**0.5
        direction = (dx / l2_norm, dy / l2_norm)
        normal_direction = (-direction[1], direction[0])

        # compute new position
        if self.K_w_pressed:
            self.pos[0] += self.speed * direction[0]
            self.pos[1] += self.speed * direction[1]

        if self.K_s_pressed:
            self.pos[0] -= self.speed * direction[0]
            self.pos[1] -= self.speed * direction[1]

        if self.K_a_pressed:
            self.pos[0] -= self.speed * normal_direction[0]
            self.pos[1] -= self.speed * normal_direction[1]

        if self.K_d_pressed:
            self.pos[0] += self.speed * normal_direction[0]
            self.pos[1] += self.speed * normal_direction[1]


def main(args):
    try:
        GAME = game(args.ip, args.port)
        GAME.start_game()
    except Exception as e:
        GAME.client.close()
        raise e
    finally:
        GAME.client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str)
    parser.add_argument("--port", type=int)
    args = parser.parse_args()

    main(args)
