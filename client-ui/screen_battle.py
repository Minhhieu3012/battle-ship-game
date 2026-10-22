import pygame
from common import Button, load_asset_image
from stat import get_state

class BattleScreen:
    def __init__(self, screen, send_queue, username, my_ships):
        self.screen = screen
        self.send_queue = send_queue
        self.username = username or get_state().get_name() or ""
        self.my_ships = my_ships or []
        self.font = pygame.font.SysFont("Arial", 28)
        self.small_font = pygame.font.SysFont("Arial", 20)
        self.big_font = pygame.font.SysFont("Arial", 48, bold=True)

        # Grid settings
        self.grid_size = 10
        self.cell_size = 30
        self.my_origin = (80, 120)
        self.enemy_origin = (450, 120)
        
        # Track shots
        self.my_shots = {}          # (x,y) -> 'miss' | 'hit' | 'sunk' (tôi bắn)
        self.enemy_shots = {}       # (x,y) -> 'miss' | 'hit' | 'sunk' (địch bắn)
        self.pending_shots = set()  # Toạ độ đang chờ server phản hồi để tránh click đúp

        # Danh sách tàu đã bị chìm để vẽ X lớn
        self.enemy_sunk_ships = []  # list[frozenset[(x,y)]]
        self.my_sunk_ships = []     # list[frozenset[(x,y)]]

        self.done = False
        self.next = None
        self.winner = None
        self.turn_info = ""
        self.error_message = ""

        # Buttons for game over
        self.play_again_btn = pygame.Rect(220, 380, 160, 50)
        self.exit_btn = pygame.Rect(440, 380, 120, 50)

        # ====== Tải ảnh tàu để vẽ ở board của tôi ======
        self.ship_images = {
            2: load_asset_image("image1.png", (2 * self.cell_size, self.cell_size)),
            3: load_asset_image("image2.png", (3 * self.cell_size, self.cell_size)),
            4: load_asset_image("image4.png", (4 * self.cell_size, self.cell_size)),
            5: load_asset_image("image5.png", (5 * self.cell_size, self.cell_size)),
        }

    def handle_event(self, event):
        if self.winner is not None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if self.play_again_btn.collidepoint(mx, my):
                    get_state().reset_game_state()
                    self.done = True
                    self.next = "lobby"
                elif self.exit_btn.collidepoint(mx, my):
                    pygame.quit()
                    exit()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            col = (mx - self.enemy_origin[0]) // self.cell_size
            row = (my - self.enemy_origin[1]) // self.cell_size
            
            if 0 <= col < self.grid_size and 0 <= row < self.grid_size:
                game_state = get_state()
                if not self.username:
                    self.username = game_state.get_name() or ""

                if game_state.is_my_turn(self.username) and (col, row) not in self.my_shots and (col, row) not in self.pending_shots:
                    self.pending_shots.add((col, row))
                    self.send_queue.put({
                        "action": "shoot",
                        "x": col,
                        "y": row
                    })

    def update(self):
        game_state = get_state()
        if not self.username:
            self.username = game_state.get_name() or ""
        
        # Check last error
        err = game_state.get_last_error()
        if err:
            self.error_message = err

        # Update shot results
        shot_results = game_state.get_shot_results()
        for shot in shot_results:
            x, y, result, by = shot["x"], shot["y"], shot["result"], shot["by"]
            self.pending_shots.discard((x, y))

            is_my_shot = (by == self.username) or (bool(self.username) and by.strip().lower() == self.username.strip().lower())
            if is_my_shot:
                self.my_shots[(x, y)] = result
                if result == 'sunk':
                    cells = self._extract_sunk_cells(shot, enemy_board=True)
                    self._add_sunk_ship(self.enemy_sunk_ships, cells)
            else:
                self.enemy_shots[(x, y)] = result
                if result == 'sunk':
                    cells = self._extract_sunk_cells(shot, enemy_board=False)
                    self._add_sunk_ship(self.my_sunk_ships, cells)
        
        if shot_results:
            game_state.clear_shot_results()
        
        # Update turn info
        if game_state.get_opponent_left():
            self.turn_info = "Opponent disconnected"
        else:
            players = game_state.get_players()
            current_turn = game_state.get_turn()
            if players and current_turn is not None and len(players) > current_turn:
                turn_player = players[current_turn]
                is_turn = (turn_player == self.username) or (bool(self.username) and turn_player.strip().lower() == self.username.strip().lower())
                self.turn_info = "Your turn" if is_turn else f"{turn_player}'s Turn"
        
        # Check for game over
        winner = game_state.get_winner()
        if winner and not self.winner:
            self.set_winner(winner)

    # ====== Helpers sunk detection & drawing ======
    def _add_sunk_ship(self, store_list, cells):
        if not cells:
            return
        new_set = frozenset(cells)
        for s in store_list:
            if s == new_set:
                return
        store_list.append(new_set)

    def _extract_sunk_cells(self, shot, enemy_board: bool):
        """
        Lấy danh sách toạ độ thuộc con tàu bị chìm.
        - Với tàu của tôi (enemy_board=False): Lấy chính xác từ self.my_ships đã đặt.
        - Với tàu của đối thủ (enemy_board=True): Dùng dữ liệu server hoặc suy luận từ shots_map.
        """
        sx, sy = shot["x"], shot["y"]

        # Nếu là tàu của mình bị chìm, đối chiếu trực tiếp từ danh sách self.my_ships
        if not enemy_board and self.my_ships:
            for ship in self.my_ships:
                pos = ship.get("pos") or ship.get("grid_pos")
                if not pos:
                    continue
                r, c = pos
                length = ship.get("length", 1)
                orient = ship.get("orientation", "H")
                if orient == "H":
                    cells = [(c + i, r) for i in range(length)]
                else:
                    cells = [(c, r + i) for i in range(length)]
                if (sx, sy) in cells:
                    return cells

        # 1) Server có thể gửi trực tiếp danh sách cell
        ship_cells = shot.get("ship_cells")
        if ship_cells:
            return [tuple(c) for c in ship_cells]

        # 2) Hoặc gửi pos/length/orientation
        ship = shot.get("ship")
        if ship and "length" in ship:
            length = ship["length"]
            orientation = ship.get("orientation", "H")
            start = ship.get("pos") or ship.get("start") or (sx, sy)
            start_x, start_y = start if isinstance(start, (list, tuple)) else (sx, sy)
            if orientation == "H":
                return [(start_x + i, start_y) for i in range(length)]
            else:
                return [(start_x, start_y + i) for i in range(length)]

        # 3) Suy luận từ lịch sử bắn (loại trừ các ô đã thuộc tàu chìm trước đó)
        base = (sx, sy)
        shots_map = self.my_shots if enemy_board else self.enemy_shots
        already_sunk = set()
        store_list = self.enemy_sunk_ships if enemy_board else self.my_sunk_ships
        for s in store_list:
            already_sunk.update(s)
        return self._infer_contiguous_ship(base, shots_map, already_sunk)

    def _infer_contiguous_ship(self, start, shots_map, already_sunk=None):
        """Suy luận con tàu bằng các ô 'hit'/'sunk' liên tiếp ngang hoặc dọc."""
        if already_sunk is None:
            already_sunk = set()
        x, y = start

        def collect_direction(dx, dy):
            cells = []
            cx, cy = x + dx, y + dy
            while (cx, cy) in shots_map and shots_map[(cx, cy)] in ("hit", "sunk") and (cx, cy) not in already_sunk:
                cells.append((cx, cy))
                cx += dx
                cy += dy
            return cells

        # Thu thập ngang
        left = collect_direction(-1, 0)
        right = collect_direction(1, 0)
        horiz = list(reversed(left)) + [(x, y)] + right

        # Thu thập dọc
        up = collect_direction(0, -1)
        down = collect_direction(0, 1)
        vert = list(reversed(up)) + [(x, y)] + down

        # Chọn hướng dài hơn (tàu luôn thẳng)
        if len(horiz) >= len(vert) and len(horiz) > 1:
            return horiz
        if len(vert) > 1:
            return vert
        # Fallback: chỉ có 1 ô
        return [(x, y)]

    def draw(self):
        self.screen.fill((20, 40, 70))

        title = self.font.render(f"Battle - {self.username}", True, (255, 255, 255))
        title_rect = title.get_rect(center=(400, 30))
        self.screen.blit(title, title_rect)

        # Turn info
        if self.turn_info and not self.winner:
            turn_color = (0, 255, 0) if "Your" in self.turn_info else (255, 255, 0)
            turn_text = self.small_font.render(self.turn_info, True, turn_color)
            turn_rect = turn_text.get_rect(center=(400, 60))
            self.screen.blit(turn_text, turn_rect)

        # Labels
        my_label = self.font.render("Your Board", True, (200, 200, 200))
        enemy_label = self.font.render("Opponent's Board", True, (200, 200, 200))
        self.screen.blit(my_label, (self.my_origin[0], 80))
        self.screen.blit(enemy_label, (self.enemy_origin[0], 80))

        # Draw grids
        self._draw_my_grid()
        self._draw_enemy_grid()

        # Game over overlay
        if self.winner is not None:
            self._draw_game_over()

        pygame.display.flip()

    def _draw_my_grid(self):
        # Lưới
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                rect = pygame.Rect(
                    self.my_origin[0] + col * self.cell_size,
                    self.my_origin[1] + row * self.cell_size,
                    self.cell_size,
                    self.cell_size
                )
                pygame.draw.rect(self.screen, (0, 150, 255), rect, 1)
        
        # Vẽ tàu (sử dụng pos từ màn setup)
        for ship in self.my_ships:
            pos = ship.get("pos") or ship.get("grid_pos")
            if not pos:
                continue
            row, col = pos
            length = ship.get("length", 1)
            orientation = ship.get("orientation", "H")

            img = self.ship_images.get(length)
            if img is None:
                w = length * self.cell_size if orientation == "H" else self.cell_size
                h = self.cell_size if orientation == "H" else length * self.cell_size
                img = pygame.Surface((w, h))
                img.fill((100, 200, 100))
            elif orientation == "V":
                img = pygame.transform.rotate(img, -90)

            pixel_pos = (
                self.my_origin[0] + col * self.cell_size,
                self.my_origin[1] + row * self.cell_size
            )
            self.screen.blit(img, pixel_pos)
        
        # Đánh dấu cú bắn của đối thủ lên bảng của tôi
        for (col, row), result in self.enemy_shots.items():
            rect = pygame.Rect(
                self.my_origin[0] + col * self.cell_size,
                self.my_origin[1] + row * self.cell_size,
                self.cell_size,
                self.cell_size
            )
            if result in ['hit', 'sunk']:
                pygame.draw.rect(self.screen, (255, 0, 0), rect, 0)
            elif result == 'miss':
                pygame.draw.circle(self.screen, (100, 100, 100), rect.center, 6)

        # Vẽ dấu X lớn cho tàu của tôi đã bị chìm
        for cells in self.my_sunk_ships:
            self._draw_big_x_over_cells(cells, self.my_origin)

    def _draw_enemy_grid(self):
        # Lưới
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                rect = pygame.Rect(
                    self.enemy_origin[0] + col * self.cell_size,
                    self.enemy_origin[1] + row * self.cell_size,
                    self.cell_size,
                    self.cell_size
                )
                pygame.draw.rect(self.screen, (255, 100, 100), rect, 1)
        
        # Cú bắn của tôi
        for (col, row), result in self.my_shots.items():
            rect = pygame.Rect(
                self.enemy_origin[0] + col * self.cell_size,
                self.enemy_origin[1] + row * self.cell_size,
                self.cell_size,
                self.cell_size
            )
            if result in ['hit', 'sunk']:
                pygame.draw.rect(self.screen, (255, 0, 0), rect)
            elif result == 'miss':
                pygame.draw.circle(self.screen, (100, 100, 100), rect.center, 8)

        # Vẽ dấu X lớn cho tàu đối thủ đã bị tôi bắn chìm
        for cells in self.enemy_sunk_ships:
            self._draw_big_x_over_cells(cells, self.enemy_origin)

    def _draw_big_x_over_cells(self, cells_set, origin):
        """Vẽ dấu X lớn phủ toàn bộ vùng bao các ô của 1 con tàu."""
        if not cells_set:
            return
        cells = list(cells_set)
        if not cells:
            return
        min_c = min(c for c, _ in cells)
        max_c = max(c for c, _ in cells)
        min_r = min(r for _, r in cells)
        max_r = max(r for _, r in cells)

        rect = pygame.Rect(
            origin[0] + min_c * self.cell_size,
            origin[1] + min_r * self.cell_size,
            (max_c - min_c + 1) * self.cell_size,
            (max_r - min_r + 1) * self.cell_size
        )
        # Vẽ X đậm
        pygame.draw.line(self.screen, (255, 255, 255), rect.topleft, rect.bottomright, 4)
        pygame.draw.line(self.screen, (255, 255, 255), rect.topright, rect.bottomleft, 4)

    def _draw_game_over(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        if self.winner == "me":
            msg = self.big_font.render("YOU WIN!", True, (0, 255, 0))
        else:
            msg = self.big_font.render("YOU LOSE!", True, (255, 50, 50))

        msg_rect = msg.get_rect(center=(400, 300))
        self.screen.blit(msg, msg_rect)

        pygame.draw.rect(self.screen, (0, 200, 0), self.play_again_btn)
        play_text = self.font.render("Play Again", True, (255, 255, 255))
        play_rect = play_text.get_rect(center=self.play_again_btn.center)
        self.screen.blit(play_text, play_rect)

        pygame.draw.rect(self.screen, (200, 0, 0), self.exit_btn)
        exit_text = self.font.render("Exit", True, (255, 255, 255))
        exit_rect = exit_text.get_rect(center=self.exit_btn.center)
        self.screen.blit(exit_text, exit_rect)

    def set_winner(self, winner: str):
        if winner in ("me", "enemy"):
            self.winner = winner
        elif bool(self.username) and winner == self.username:
            self.winner = "me"
        else:
            self.winner = "enemy"
