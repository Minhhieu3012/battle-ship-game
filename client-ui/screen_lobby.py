import pygame
from common import Button
from stat import get_state

class LobbyScreen:
    def __init__(self, screen, send_queue, username):
        self.screen = screen
        self.send_queue = send_queue
        self.username = username
        self.font = pygame.font.SysFont("Arial", 32)
        self.small_font = pygame.font.SysFont("Arial", 20)

        self.create_button = Button(250, 250, 300, 50, "Create Room")
        self.join_button = Button(250, 320, 300, 50, "Join Room")
        self.quit_button = Button(250, 390, 300, 50, "Quit Game")

        self.done = False
        self.next = None
        self.data = {}

    def handle_event(self, event):
        if self.create_button.handle_event(event):
            self.done = True
            self.next = "create_room"
            self.data = {"username": self.username}

        if self.join_button.handle_event(event):
            self.done = True
            self.next = "join_room"
            self.data = {"username": self.username}
            
        if self.quit_button.handle_event(event):
            pygame.quit()
            exit()

    def update(self):
        # Check if we've joined a room automatically
        game_state = get_state()
        if game_state.get_joined():
            self.done = True
            self.next = "setup"

    def draw(self):
        self.screen.fill((50, 50, 100))
        
        title = self.font.render(f"Welcome, {self.username}", True, (255, 255, 255))
        title_rect = title.get_rect(center=(400, 150))
        self.screen.blit(title, title_rect)

        self.create_button.draw(self.screen)
        self.join_button.draw(self.screen)
        self.quit_button.draw(self.screen)
        
        # Show connection status
        game_state = get_state()
        if game_state.get_connected():
            status = self.small_font.render("Connected to server", True, (0, 255, 0))
        else:
            error = game_state.get_connection_error()
            status_text = f"Connection lost: {error}" if error else "Disconnected from server"
            status = self.small_font.render(status_text, True, (255, 0, 0))
        
        status_rect = status.get_rect(center=(400, 500))
        self.screen.blit(status, status_rect)

        pygame.display.flip()