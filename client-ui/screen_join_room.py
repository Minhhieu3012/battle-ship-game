import pygame
from common import Button, InputBox
from state import get_state

class JoinRoomScreen:
    def __init__(self, screen, send_queue, username):
        self.screen = screen
        self.send_queue = send_queue
        self.username = username
        self.font = pygame.font.SysFont("Arial", 32)
        self.small_font = pygame.font.SysFont("Arial", 20)

        self.input_box = InputBox(250, 270, 300, 50)
        self.join_button = Button(250, 350, 300, 50, "Join")
        self.back_button = Button(250, 420, 300, 50, "Back")

        self.done = False
        self.next = None
        self.error_message = ""

    def handle_event(self, event):
        result = self.input_box.handle_event(event)
        if result:  # Enter pressed
            if self.input_box.text.strip():
                self._join_room(self.input_box.text.strip())

        if self.join_button.handle_event(event):
            if self.input_box.text.strip():
                self._join_room(self.input_box.text.strip())
                
        if self.back_button.handle_event(event):
            self.done = True
            self.next = "lobby"

    def _join_room(self, code):
        self.send_queue.put({"action": "join_room", "name": self.username, "room_id": code})
        self.error_message = "Joining room..."

    def update(self):
        self.input_box.update()
        
        game_state = get_state()
        if game_state.get_joined():
            self.done = True
            self.next = "setup"
        
        error = game_state.get_last_error()
        if error:
            if "full" in error.lower():
                self.error_message = "Room is full!"
            elif "not exist" in error.lower() or "not found" in error.lower():
                self.error_message = "Room does not exist!"
            else:
                self.error_message = error

    def draw(self):
        self.screen.fill((50, 50, 100))
        
        title = self.font.render("Enter Room Code:", True, (255, 255, 255))
        title_rect = title.get_rect(center=(400, 220))
        self.screen.blit(title, title_rect)
        
        self.input_box.draw(self.screen)
        self.join_button.draw(self.screen)
        self.back_button.draw(self.screen)
        
        if self.error_message:
            color = (255, 0, 0) if any(word in self.error_message.lower() for word in ["error", "full", "exist"]) else (255, 255, 0)
            error_text = self.small_font.render(self.error_message, True, color)
            error_rect = error_text.get_rect(center=(400, 500))
            self.screen.blit(error_text, error_rect)

        pygame.display.flip()