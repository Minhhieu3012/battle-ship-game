import pygame
from common import Button, load_asset_image
from state import get_state

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

        # Danh sach tau (ngang) theo do dai
        self.ships_data = [
            {"length": 2},  # image1.png
            {"length": 3},  # image2.png
            {"length": 3},  # image3.png
            {"length": 4},  # image4.png
            {"length": 5},  # image5.png
        ]

        # Ten file anh khop voi danh sach tren
        self.ship_image_files = [
            "image1.png",
            "image2.png",
            "image3.png",
            "image4.png",
            "image5.png",
        ]

        # Khoi tao tau o khu dock ben phai luoi
        self.ships = []
        start_x = self.grid_origin[0] + self.grid_size * self.cell_size + 50
        start_y = 100
        gap = 15

        # Luu thong tin dock de ve huong dan
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
                "idx": idx,
                "rect": rect,
                "length": length,
                "image": img,
                "orientation": "H",
                "placed": False,
                "grid_pos": None,
                "original_pos": (rect.x, rect.y),
                "original_orientation": "H",
            })

        # Dragging
        self.dragging_ship = None
        self.offset_x = 0
        self.offset_y = 0

        # Click detection: phan biet click ngan (xoay) vs keo dai (dat)
        self._mouse_down_pos = None
        self._mouse_down_ship = None

        self.done = False
        self.next = None
        self.placed_ships = []

        self.ready_sent = False
        self.status_message = ""
        self.error_message = ""

    def handle_event(self, event):
        # Kiem tra back/ready button TRUOC khi xu ly drag-drop de tranh xung dot
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button.handle_event(event):
                get_state().reset_game_state()
                self.done = True
                self.next = "lobby"
                return
            if self.ready_button.handle_event(event) and not self.ready_sent:
                self._send_ready()
                return

            # Bat dau drag; ghi nhan mouse_down de phan biet click/drag
            for ship in reversed(self.ships):
                if ship["rect"].collidepoint(event.pos):
                    self._mouse_down_pos = event.pos
                    self._mouse_down_ship = ship
                    self.dragging_ship = ship
                    mx, my = event.pos
                    self.offset_x = ship["rect"].x - mx
                    self.offset_y = ship["rect"].y - my
                    break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_ship:
                drag_dist = 0
                if self._mouse_down_pos:
                    dx = event.pos[0] - self._mouse_down_pos[0]
                    dy = event.pos[1] - self._mouse_down_pos[1]
                    drag_dist = (dx*dx + dy*dy) ** 0.5

                if drag_dist < 8 and self._mouse_down_ship is self.dragging_ship:
                    # Click ngan -> xoay tau
                    self._rotate_ship(self.dragging_ship)
                else:
                    # Keo tha -> snap vao luoi
                    self._handle_ship_placement()

                self.dragging_ship = None
                self._mouse_down_pos = None
                self._mouse_down_ship = None

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_ship:
                mx, my = event.pos
                self.dragging_ship["rect"].x = mx + self.offset_x
                self.dragging_ship["rect"].y = my + self.offset_y

    def _rotate_ship(self, ship):
        """Xoay tau 90 do: H -> V -> H."""
        idx = ship["idx"]
        length = ship["length"]
        old_center = ship["rect"].center

        if ship["orientation"] == "H":
            ship["orientation"] = "V"
            h_img = load_asset_image(
                self.ship_image_files[idx],
                size=(length * self.cell_size, self.cell_size)
            )
            new_img = pygame.transform.rotate(h_img, 90)
        else:
            ship["orientation"] = "H"
            new_img = load_asset_image(
                self.ship_image_files[idx],
                size=(length * self.cell_size, self.cell_size)
            )

        ship["image"] = new_img
        ship["rect"] = new_img.get_rect(center=old_center)

        # Neu tau dang dat tren luoi, validate lai; neu khong hop le thi reset
        if ship["placed"] and ship["grid_pos"] is not None:
            row, col = ship["grid_pos"]
            if not self._is_valid_placement(ship, row, col, exclude=ship):
                self._reset_ship_position(ship)

    def _handle_ship_placement(self):
        ship = self.dragging_ship
        ship_x, ship_y = ship["rect"].topleft
        col = round((ship_x - self.grid_origin[0]) / self.cell_size)
        row = round((ship_y - self.grid_origin[1]) / self.cell_size)

        if self._is_valid_placement(ship, row, col, exclude=ship):
            snap_x = self.grid_origin[0] + col * self.cell_size
            snap_y = self.grid_origin[1] + row * self.cell_size
            ship["rect"].topleft = (snap_x, snap_y)
            ship["placed"] = True
            ship["grid_pos"] = (row, col)
        else:
            self._reset_ship_position(ship)

    def _is_valid_placement(self, ship, row, col, exclude=None):
        """Kiem tra tau co nam trong luoi va khong va cham voi tau khac."""
        length = ship["length"]
        orientation = ship["orientation"]

        if orientation == "H":
            if not (0 <= col <= self.grid_size - length and 0 <= row < self.grid_size):
                return False
            cells = set((row, col + i) for i in range(length))
        else:  # V
            if not (0 <= col < self.grid_size and 0 <= row <= self.grid_size - length):
                return False
            cells = set((row + i, col) for i in range(length))

        for other_ship in self.ships:
            if other_ship is exclude or not other_ship["placed"]:
                continue
            other_cells = self._get_ship_cells(other_ship)
            if cells & other_cells:
                return False
        return True

    def _get_ship_cells(self, ship):
        """Lay tap hop (row, col) cac o ma tau chiem."""
        if not ship["placed"] or ship["grid_pos"] is None:
            return set()
        row, col = ship["grid_pos"]
        length = ship["length"]
        orientation = ship["orientation"]
        if orientation == "H":
            return set((row, col + i) for i in range(length))
        else:
            return set((row + i, col) for i in range(length))

    def _reset_ship_position(self, ship=None):
        if ship is None:
            ship = self.dragging_ship
        ship["orientation"] = ship["original_orientation"]
        idx = ship["idx"]
        length = ship["length"]
        ship["image"] = load_asset_image(
            self.ship_image_files[idx],
            size=(length * self.cell_size, self.cell_size)
        )
        ship["rect"] = ship["image"].get_rect(topleft=ship["original_pos"])
        ship["placed"] = False
        ship["grid_pos"] = None

    def _send_ready(self):
        placed_ships = []
        for ship in self.ships:
            if ship["placed"]:
                row, col = ship["grid_pos"]
                placed_ships.append({
                    "length": ship["length"],
                    "pos": (row, col),
                    "orientation": ship["orientation"],
                })
        self.placed_ships = placed_ships
        self.send_queue.put({
            "action": "ready",
            "name": self.username,
            "ships": placed_ships,
        })
        self.ready_sent = True
        self.status_message = "Ready signal sent, waiting for opponent..."

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

        # Highlight o hop le/khong hop le khi dang keo tau
        if self.dragging_ship:
            sx, sy = self.dragging_ship["rect"].topleft
            hl_col = round((sx - self.grid_origin[0]) / self.cell_size)
            hl_row = round((sy - self.grid_origin[1]) / self.cell_size)
            valid = self._is_valid_placement(self.dragging_ship, hl_row, hl_col, exclude=self.dragging_ship)
            hl_color = (0, 220, 80, 100) if valid else (220, 60, 60, 100)
            hl_len = self.dragging_ship["length"]
            hl_orient = self.dragging_ship["orientation"]
            hl_surf = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
            hl_surf.fill(hl_color)
            if hl_orient == "H":
                for i in range(hl_len):
                    px = self.grid_origin[0] + (hl_col + i) * self.cell_size
                    py = self.grid_origin[1] + hl_row * self.cell_size
                    if 0 <= hl_col + i < self.grid_size and 0 <= hl_row < self.grid_size:
                        self.screen.blit(hl_surf, (px, py))
            else:
                for i in range(hl_len):
                    px = self.grid_origin[0] + hl_col * self.cell_size
                    py = self.grid_origin[1] + (hl_row + i) * self.cell_size
                    if 0 <= hl_col < self.grid_size and 0 <= hl_row + i < self.grid_size:
                        self.screen.blit(hl_surf, (px, py))

        # Ve tau (anh)
        for ship in self.ships:
            if ship is self.dragging_ship:
                border_rect = ship["rect"].inflate(4, 4)
                pygame.draw.rect(self.screen, (0, 255, 120), border_rect, 2, border_radius=3)
            self.screen.blit(ship["image"], ship["rect"])

        # Hint text ben duoi dock
        hint_color = (180, 220, 255)
        hint = self.small_font.render("Click ship to rotate  |  Drag to grid", True, hint_color)
        self.screen.blit(hint, (self.dock_x, self.dock_end_y + 18))
        placed_count = sum(1 for s in self.ships if s["placed"])
        count_text = self.small_font.render(
            f"Ships placed: {placed_count}/{len(self.ships)}", True, (200, 200, 200)
        )
        self.screen.blit(count_text, (self.dock_x, self.dock_end_y + 44))

        # Ready button chi sang khi dat het tau
        all_placed = all(ship["placed"] for ship in self.ships)
        if all_placed and not self.ready_sent:
            self.ready_button.color = (0, 160, 0)
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
