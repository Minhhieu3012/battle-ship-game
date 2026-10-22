import pygame
from common import Button, load_asset_image
from stat import get_state

class SetupScreen:
    def __init__(self, screen, send_queue, username):
        self.screen = screen
        self.send_queue = send_queue
        self.username = username
        self.font = pygame.font.SysFont("Arial", 28)
        self.small_font = pygame.font.SysFont("Arial", 20)

        self.ready_button = Button(300, 500, 200, 50, "Ready")
        self.back_button = Button(520, 500, 200, 50, "Back")

        # Grid
        self.grid_size = 10
        self.cell_size = 35
        self.grid_origin = (50, 100)

        # Danh sách tàu (ngang) theo độ dài
        self.ships_data = [
            {"length": 2},  # image1.png
            {"length": 3},  # image2.png
            {"length": 3},  # image3.png
            {"length": 4},  # image4.png
            {"length": 5},  # image5.png
        ]

        # Tên file ảnh khớp với danh sách trên
        self.ship_image_files = [
            "image1.png",
            "image2.png",
            "image3.png",
            "image4.png",
            "image5.png",
        ]
        
        # Khởi tạo object tàu để kéo/thả
        self.ships = []
        start_x = self.grid_origin[0] + self.grid_size * self.cell_size + 50
        start_y = 100
        gap = 15

        # Lưu thông tin dock để vẽ hướng dẫn
        self.dock_x = start_x
        self.dock_y = start_y
        self.dock_gap = gap
        self.dock_end_y = (
            self.dock_y
            + len(self.ships_data) * self.cell_size
            + (len(self.ships_data) - 1) * self.dock_gap
        )

        for idx, ship_data in enumerate(self.ships_data):
            length = ship_data["length"]
            img = load_asset_image(
                self.ship_image_files[idx],
                size=(length * self.cell_size, self.cell_size)
            )
            rect = img.get_rect()
            rect.topleft = (start_x, start_y + idx * (self.cell_size + gap))

            self.ships.append({
                "rect": rect,
                "length": length,
                "image": img,
                "placed": False,
                "grid_pos": None,
                "original_pos": (rect.x, rect.y)
            })

        # Dragging
        self.dragging_ship = None
        self.offset_x = 0
        self.offset_y = 0

        self.done = False
        self.next = None
        self.placed_ships = []
        
        self.ready_sent = False
        self.status_message = ""
        self.error_message = ""

    def handle_event(self, event):
        if self.ready_button.handle_event(event) and not self.ready_sent:
            self._send_ready()
            
        if self.back_button.handle_event(event):
            self.done = True
            self.next = "lobby"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Bắt đầu kéo tàu
            for ship in reversed(self.ships):  # ưu tiên tàu trên cùng
                if ship["rect"].collidepoint(event.pos):
                    self.dragging_ship = ship
                    mx, my = event.pos
                    self.offset_x = ship["rect"].x - mx
                    self.offset_y = ship["rect"].y - my
                    break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_ship:
                self._handle_ship_placement()
                self.dragging_ship = None

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_ship:
                mx, my = event.pos
                self.dragging_ship["rect"].x = mx + self.offset_x
                self.dragging_ship["rect"].y = my + self.offset_y

    def _send_ready(self):
        # Gom danh sách tàu đã đặt lên lưới
        placed_ships = []
        for ship in self.ships:
            if ship["placed"]:
                row, col = ship["grid_pos"]
                placed_ships.append({
                    "length": ship["length"],
                    "pos": (row, col),
                    "orientation": "H"  # phiên bản đơn giản: nằm ngang
                })

        self.placed_ships = placed_ships
        self.send_queue.put({
            "action": "ready",
            "name": self.username,
            "ships": placed_ships
        })
        self.ready_sent = True
        self.status_message = "Ready signal sent, waiting for opponent..."

    def _handle_ship_placement(self):
        # Snap tàu vào lưới nếu hợp lệ
        ship_x, ship_y = self.dragging_ship["rect"].topleft
        col = round((ship_x - self.grid_origin[0]) / self.cell_size)
        row = round((ship_y - self.grid_origin[1]) / self.cell_size)
        length = self.dragging_ship["length"]

        if (0 <= col <= self.grid_size - length and 0 <= row < self.grid_size):
            # Kiểm tra va chạm với các tàu đã đặt (ngang)
            collision = False
            for other_ship in self.ships:
                if other_ship is self.dragging_ship or not other_ship["placed"]:
                    continue
                other_row, other_col = other_ship["grid_pos"]
                other_len = other_ship["length"]
                if row == other_row:
                    if not (col >= other_col + other_len or col + length <= other_col):
                        collision = True
                        break

            if not collision:
                snap_x = self.grid_origin[0] + col * self.cell_size
                snap_y = self.grid_origin[1] + row * self.cell_size
                self.dragging_ship["rect"].topleft = (snap_x, snap_y)
                self.dragging_ship["placed"] = True
                self.dragging_ship["grid_pos"] = (row, col)
            else:
                self._reset_ship_position()
        else:
            self._reset_ship_position()

    def _reset_ship_position(self):
        # Trả tàu về vị trí ban đầu nếu đặt sai
        self.dragging_ship["rect"].topleft = self.dragging_ship["original_pos"]
        self.dragging_ship["placed"] = False
        self.dragging_ship["grid_pos"] = None

    def update(self):
        game_state = get_state()
        
        # Bắt đầu trận nếu server báo start
        if game_state.get_started():
            self.done = True
            self.next = "battle"
        
        # Trạng thái
        players = game_state.get_players()
        if len(players) < 2:
            self.status_message = "Waiting for the second player..."
        elif self.ready_sent:
            ready_count = game_state.get_ready_count()
            self.status_message = f"Ready ({ready_count}/2)"
        
        # Lỗi
        error = game_state.get_last_error()
        if error:
            self.error_message = error

    def draw(self):
        self.screen.fill((30, 30, 60))

        # Title
        title = self.font.render(f"Setup Your Ships - {self.username}", True, (255, 255, 255))
        self.screen.blit(title, (250, 30))

        # Lưới
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                rect = pygame.Rect(
                    self.grid_origin[0] + col * self.cell_size,
                    self.grid_origin[1] + row * self.cell_size,
                    self.cell_size,
                    self.cell_size
                )
                pygame.draw.rect(self.screen, (100, 150, 200), rect, 1)

        # Vẽ tàu (ảnh)
        for ship in self.ships:
            self.screen.blit(ship["image"], ship["rect"])

        # Hướng dẫn — hiển thị dưới các thuyền
        instructions = [
            "Drag and drop ships onto the grid",
            f"Place all {len(self.ships)} ships to get ready"
        ]
        instr_x = self.dock_x
        instr_y = self.dock_end_y + 20
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, (200, 200, 200))
            self.screen.blit(text, (instr_x, instr_y + i * 22))

        # Ready button
        all_placed = all(ship["placed"] for ship in self.ships)
        if all_placed and not self.ready_sent:
            self.ready_button.color = (0, 150, 0)
        elif self.ready_sent:
            self.ready_button.color = (100, 100, 100)
        else:
            self.ready_button.color = (100, 100, 100)
        
        self.ready_button.draw(self.screen)
        self.back_button.draw(self.screen)

        # Status & error
        if self.status_message:
            status_text = self.small_font.render(self.status_message, True, (255, 255, 0))
            status_rect = status_text.get_rect(center=(400, 570))
            self.screen.blit(status_text, status_rect)
        
        if self.error_message:
            error_text = self.small_font.render(self.error_message, True, (255, 0, 0))
            error_rect = error_text.get_rect(center=(400, 540))
            self.screen.blit(error_text, error_rect)
        
        # Thông tin người chơi
        game_state = get_state()
        players = game_state.get_players()
        if players:
            player_info = self.small_font.render(f"Players: {', '.join(players)}", True, (150, 150, 150))
            self.screen.blit(player_info, (50, 60))

        pygame.display.flip()
