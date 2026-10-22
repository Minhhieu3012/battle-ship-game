import sys
import pygame
from pathlib import Path

# ====== Asset utils (đường dẫn ảnh) ======
if getattr(sys, "frozen", False):
    base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    _ASSETS_DIR = base_dir / "images"
    if not _ASSETS_DIR.exists():
        _ASSETS_DIR = Path(sys.executable).parent / "images"
else:
    _ASSETS_DIR = Path(__file__).resolve().parent / "images"

def asset_path(filename: str) -> Path:
    # Trả về path tuyệt đối tới ảnh trong thư mục client-ui/images
    return _ASSETS_DIR / filename

def load_asset_image(filename: str, size=None) -> pygame.Surface:
    """
    Load ảnh từ thư mục images, có thể scale về kích thước 'size' (w, h).
    Nếu thiếu file, tạo surface fallback để không crash.
    """
    try:
        img = pygame.image.load(str(asset_path(filename))).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        # Fallback: khối màu (không viền) để tránh lỗi thiếu file
        w, h = size if size else (60, 30)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((120, 120, 120, 220))
        return surf

class Button:
    def __init__(self, x, y, w, h, text):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = (70, 130, 180)
        self.hover_color = (100, 160, 210)
        self.font = pygame.font.SysFont("Arial", 24)
        self.hovered = False

    def draw(self, screen):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 2)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        screen.blit(text_surf, text_surf.get_rect(center=self.rect.center))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = (100, 100, 100)
        self.color_active = (255, 255, 255)
        self.color = self.color_inactive
        self.text = text
        self.font = pygame.font.SysFont("Arial", 24)
        self.txt_surface = self.font.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Toggle active
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = self.color_active if self.active else self.color_inactive

        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return self.text  # Return text on Enter
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render the text
                self.txt_surface = self.font.render(self.text, True, self.color)
        return None

    def update(self):
        # Resize the box if the text is too long
        width = max(200, self.txt_surface.get_width()+10)
        self.rect.w = width

    def draw(self, screen):
        # Blit the text
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
        # Blit the rect
        pygame.draw.rect(screen, self.color, self.rect, 2)
