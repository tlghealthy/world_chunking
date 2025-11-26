"""
Elegant 2D Chunk Loading/Unloading Demo
========================================
Demonstrates loading/unloading world chunks around a player.
Chunks within a 3x3 grid around the player are loaded; others are unloaded.
"""

import pygame
import hashlib
from dataclasses import dataclass

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1920, 1080
CHUNK_SIZE = 100
PLAYER_RADIUS = 15
PLAYER_SPEED = 4

# Colors
BG_COLOR = (18, 18, 24)
CHUNK_BORDER = (60, 70, 90)
CHUNK_FILL = (30, 35, 48)
PLAYER_COLOR = (255, 120, 80)
TEXT_COLOR = (180, 190, 210)
COORD_COLOR = (100, 180, 255)
HASH_COLOR = (255, 180, 100)


@dataclass
class Chunk:
    """Represents a single world chunk."""
    x: int
    y: int
    hash_id: str
    
    @classmethod
    def create(cls, x: int, y: int) -> 'Chunk':
        """Factory method to create a chunk with computed hash."""
        coord_str = f"({x},{y})"
        hash_id = hashlib.md5(coord_str.encode()).hexdigest()[:8]
        print(f"[LOAD] Chunk {coord_str} created with hash {hash_id}")
        return cls(x, y, hash_id)
    
    def __del__(self):
        print(f"[UNLOAD] Chunk ({self.x},{self.y}) destroyed")


class ChunkManager:
    """Manages chunk loading/unloading around player position."""
    
    def __init__(self):
        self.chunks: dict[tuple[int, int], Chunk] = {}
    
    def get_required_chunks(self, center_x: int, center_y: int) -> set[tuple[int, int]]:
        """Returns the set of chunk coordinates needed for a 3x3 grid around center."""
        return {
            (center_x + dx, center_y + dy)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
        }
    
    def update(self, player_chunk_x: int, player_chunk_y: int):
        """Load/unload chunks based on player's current chunk position."""
        required = self.get_required_chunks(player_chunk_x, player_chunk_y)
        current = set(self.chunks.keys())
        
        # Unload chunks no longer needed
        for coord in current - required:
            del self.chunks[coord]
        
        # Load new chunks
        for coord in required - current:
            self.chunks[coord] = Chunk.create(*coord)
    
    def __iter__(self):
        return iter(self.chunks.values())


class Player:
    """The player entity with world position."""
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    @property
    def chunk_coords(self) -> tuple[int, int]:
        """Returns which chunk the player is currently in."""
        return (int(self.x // CHUNK_SIZE), int(self.y // CHUNK_SIZE))
    
    def move(self, dx: float, dy: float):
        self.x += dx
        self.y += dy


class Game:
    """Main game class handling rendering and input."""
    
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Chunk Loading Demo - WASD to move")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)
        self.font_large = pygame.font.SysFont("Consolas", 18, bold=True)
        
        # Start player at origin (will be in chunk 0,0)
        self.player = Player(CHUNK_SIZE // 2, CHUNK_SIZE // 2)
        self.chunk_manager = ChunkManager()
        
        # Initial chunk load
        self.chunk_manager.update(*self.player.chunk_coords)
        self.last_chunk = self.player.chunk_coords
        
        # Camera offset to center view
        self.camera_offset = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
    
    def handle_input(self):
        """Process keyboard input for player movement."""
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] - keys[pygame.K_a]) * PLAYER_SPEED
        dy = (keys[pygame.K_s] - keys[pygame.K_w]) * PLAYER_SPEED
        
        if dx or dy:
            self.player.move(dx, dy)
            
            # Check if player entered a new chunk
            current_chunk = self.player.chunk_coords
            if current_chunk != self.last_chunk:
                self.chunk_manager.update(*current_chunk)
                self.last_chunk = current_chunk
    
    def world_to_screen(self, world_x: float, world_y: float) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates (camera follows player)."""
        screen_x = world_x - self.player.x + self.camera_offset[0]
        screen_y = world_y - self.player.y + self.camera_offset[1]
        return (int(screen_x), int(screen_y))
    
    def render_chunk(self, chunk: Chunk):
        """Render a single chunk with its coordinates and hash."""
        # Calculate chunk's world position
        world_x = chunk.x * CHUNK_SIZE
        world_y = chunk.y * CHUNK_SIZE
        screen_x, screen_y = self.world_to_screen(world_x, world_y)
        
        # Draw chunk rectangle
        rect = pygame.Rect(screen_x, screen_y, CHUNK_SIZE, CHUNK_SIZE)
        pygame.draw.rect(self.screen, CHUNK_FILL, rect)
        pygame.draw.rect(self.screen, CHUNK_BORDER, rect, 2)
        
        # Render coordinate text
        coord_text = f"({chunk.x}, {chunk.y})"
        coord_surface = self.font.render(coord_text, True, COORD_COLOR)
        coord_rect = coord_surface.get_rect(center=(screen_x + CHUNK_SIZE//2, screen_y + CHUNK_SIZE//2 - 10))
        self.screen.blit(coord_surface, coord_rect)
        
        # Render hash text
        hash_surface = self.font.render(chunk.hash_id, True, HASH_COLOR)
        hash_rect = hash_surface.get_rect(center=(screen_x + CHUNK_SIZE//2, screen_y + CHUNK_SIZE//2 + 10))
        self.screen.blit(hash_surface, hash_rect)
    
    def render_player(self):
        """Render the player circle at screen center."""
        pygame.draw.circle(self.screen, PLAYER_COLOR, self.camera_offset, PLAYER_RADIUS)
        pygame.draw.circle(self.screen, (255, 255, 255), self.camera_offset, PLAYER_RADIUS, 2)
    
    def render_hud(self):
        """Render HUD information."""
        chunk_x, chunk_y = self.player.chunk_coords
        texts = [
            f"Player World Pos: ({self.player.x:.0f}, {self.player.y:.0f})",
            f"Current Chunk: ({chunk_x}, {chunk_y})",
            f"Loaded Chunks: {len(self.chunk_manager.chunks)}",
            "Move: WASD | ESC: Quit"
        ]
        
        for i, text in enumerate(texts):
            surface = self.font_large.render(text, True, TEXT_COLOR)
            self.screen.blit(surface, (20, 20 + i * 25))
    
    def render(self):
        """Render the entire scene."""
        self.screen.fill(BG_COLOR)
        
        # Render all loaded chunks
        for chunk in self.chunk_manager:
            self.render_chunk(chunk)
        
        self.render_player()
        self.render_hud()
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            self.handle_input()
            self.render()
            self.clock.tick(60)
        
        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()

