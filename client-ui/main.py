# main.py — tích hợp với client-network/network.py (chuẩn actions: join, place_ship, ready, shoot)
import os
import sys
from pathlib import Path
import pygame
from queue import Queue

# ----- Thêm đường dẫn tới thư mục 'client-network' (nếu chạy mã nguồn Python) -----
if not getattr(sys, "frozen", False):
    BASE = Path(__file__).resolve().parent.parent    # Lên thư mục cha (Group17-BattleShip)
    NET_DIR = BASE / "client-network"                # .../Group17-BattleShip/client-network

    if NET_DIR.exists():
        sys.path.append(str(NET_DIR))
    else:
        print("[FATAL] Không tìm thấy thư mục 'client-network' cạnh 'client-ui'.")
        raise SystemExit(1)

# Import module mạng chuẩn (network.py)
from network import start_network, get_state_proxy

# ----- Import các màn hình UI -----
from screen_login import LoginScreen
from screen_lobby import LobbyScreen
from screen_setup import SetupScreen
from screen_battle import BattleScreen
from screen_create_room import CreateRoomScreen
from screen_join_room import JoinRoomScreen

# ----- Khởi tạo Pygame -----
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("BattleShip Multiplayer")
clock = pygame.time.Clock()

# ----- Networking -----
send_queue = Queue()

# Cho phép đổi nhanh host/port bằng biến môi trường
NET_HOST = os.environ.get("BS_HOST", "127.0.0.1")
NET_PORT = int(os.environ.get("BS_PORT", "8000"))
_client = start_network(send_queue, host=NET_HOST, port=NET_PORT)

# (tuỳ chọn) Lấy state mạng nếu UI cần
_game_state = get_state_proxy()

# ----- State machine chuyển màn hình -----
running = True
username = ""
current_screen = LoginScreen(screen, send_queue)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        else:
            if hasattr(current_screen, "handle_event"):
                current_screen.handle_event(event)

    if hasattr(current_screen, "update"):
        current_screen.update()
    if hasattr(current_screen, "draw"):
        current_screen.draw()

    # Check for network-driven screen transitions
    if _game_state.get_game_phase() == "battle" and not isinstance(current_screen, BattleScreen):
        # Game has started, switch to battle screen
        if hasattr(current_screen, 'placed_ships'):
            current_screen = BattleScreen(screen, send_queue, username, current_screen.placed_ships)
        else:
            current_screen = BattleScreen(screen, send_queue, username, [])

    # Check for winner and game over
    winner = _game_state.get_winner()
    if winner and isinstance(current_screen, BattleScreen):
        if winner == username:
            current_screen.set_winner("me")
        else:
            current_screen.set_winner("enemy")

    # Check for opponent left
    if _game_state.get_opponent_left():
        print("[INFO] Đối thủ đã rời game, quay về lobby")
        current_screen = LobbyScreen(screen, send_queue, username)
        _game_state.set_opponent_left(False)

    # Manual screen transitions
    if getattr(current_screen, "done", False):
        nxt = getattr(current_screen, "next", None)

        # Lấy username từ màn hình login khi chuyển sang lobby
        if isinstance(current_screen, LoginScreen):
            username = getattr(current_screen, "username", "") or username

        if nxt == "lobby":
            current_screen = LobbyScreen(screen, send_queue, username)
        elif nxt == "create_room":
            current_screen = CreateRoomScreen(screen, send_queue, username)
        elif nxt == "join_room":
            current_screen = JoinRoomScreen(screen, send_queue, username)
        elif nxt == "setup":
            current_screen = SetupScreen(screen, send_queue, username)
        elif nxt == "battle":
            if hasattr(current_screen, 'placed_ships'):
                current_screen = BattleScreen(screen, send_queue, username, current_screen.placed_ships)
            else:
                current_screen = BattleScreen(screen, send_queue, username, [])
        else:
            current_screen = LobbyScreen(screen, send_queue, username) if username else LoginScreen(screen, send_queue)

    clock.tick(60)

pygame.quit()
