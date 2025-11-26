"""
Elegant 2D Chunk Loading/Unloading Demo
========================================
Demonstrates loading/unloading world chunks around a player.
Uses a hex-like offset pattern (7 chunks) for more circular coverage.
"""

import pygame
import hashlib
import math
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
CHUNK_PENDING_UNLOAD = (60, 30, 35)  # Reddish - queued for removal
CHUNK_PENDING_LOAD = (30, 50, 35)    # Greenish - ghost of incoming chunk
PLAYER_COLOR = (255, 120, 80)
TEXT_COLOR = (180, 190, 210)
COORD_COLOR = (100, 180, 255)
HASH_COLOR = (255, 180, 100)

# Slowmo settings
SLOWMO_INTERVAL = 20  # Frames between operations


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
        # Queues for slowmo mode (FIFO order)
        self.load_queue: list[tuple[int, int]] = []
        self.unload_queue: list[tuple[int, int]] = []
        # Track what's currently required (for rendering pending states)
        self.required: set[tuple[int, int]] = set()
    
    def get_required_chunks(self, center_x: int, center_y: int, hex_mode: bool = True) -> set[tuple[int, int]]:
        """Returns required chunks around player position."""
        if not hex_mode:
            # Regular 3x3 grid (9 chunks)
            return {
                (center_x + dx, center_y + dy)
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
            }
        
        # Hex-like pattern (7 chunks - drops 2 far corners)
        chunks = set()
        
        # Current row - all 3 chunks
        for dx in (-1, 0, 1):
            chunks.add((center_x + dx, center_y))
        
        # Adjacent rows - only 2 each (hex offset pattern)
        for dy in (-1, 1):
            if center_y % 2 == 0:
                # Even row: neighbors are at x-1 and x
                chunks.add((center_x - 1, center_y + dy))
                chunks.add((center_x, center_y + dy))
            else:
                # Odd row: neighbors are at x and x+1
                chunks.add((center_x, center_y + dy))
                chunks.add((center_x + 1, center_y + dy))
        
        return chunks
    
    def update(self, player_chunk_x: int, player_chunk_y: int, hex_mode: bool = True, slowmo: bool = False):
        """Load/unload chunks based on player's current chunk position."""
        self.required = self.get_required_chunks(player_chunk_x, player_chunk_y, hex_mode)
        current = set(self.chunks.keys())
        
        to_unload = current - self.required
        to_load = self.required - current
        
        if slowmo:
            # Queue operations - add new items, remove cancelled ones
            # Add to unload queue (if not already queued)
            for coord in to_unload:
                if coord not in self.unload_queue:
                    self.unload_queue.append(coord)
            
            # Add to load queue (if not already queued or loaded)
            for coord in to_load:
                if coord not in self.load_queue and coord not in self.chunks:
                    self.load_queue.append(coord)
            
            # Cancel loads that are no longer needed
            self.load_queue = [c for c in self.load_queue if c in self.required]
            
            # Cancel unloads for chunks that are needed again
            self.unload_queue = [c for c in self.unload_queue if c not in self.required]
        else:
            # Immediate mode - clear queues and execute all
            self.load_queue.clear()
            self.unload_queue.clear()
            
            for coord in to_unload:
                del self.chunks[coord]
            
            for coord in to_load:
                self.chunks[coord] = Chunk.create(*coord)
    
    def process_slowmo_tick(self) -> str | None:
        """Process one queued operation. Returns description or None."""
        # Prioritize unloads (free memory first), then loads
        if self.unload_queue:
            coord = self.unload_queue.pop(0)
            if coord in self.chunks:
                del self.chunks[coord]
                return f"Unloaded {coord}"
        elif self.load_queue:
            coord = self.load_queue.pop(0)
            if coord not in self.chunks:
                self.chunks[coord] = Chunk.create(*coord)
                return f"Loaded {coord}"
        return None
    
    def is_pending_unload(self, coord: tuple[int, int]) -> bool:
        """Check if a chunk is queued for unloading."""
        return coord in self.unload_queue
    
    def get_pending_loads(self) -> list[tuple[int, int]]:
        """Get list of chunks waiting to be loaded."""
        return self.load_queue.copy()
    
    @property
    def queue_status(self) -> str:
        """Return a string describing queue state."""
        return f"Load: {len(self.load_queue)} | Unload: {len(self.unload_queue)}"
    
    def __iter__(self):
        return iter(self.chunks.values())


class Player:
    """The player entity with world position."""
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def get_chunk_coords(self, hex_mode: bool = True) -> tuple[int, int]:
        """Returns which chunk the player is currently in."""
        chunk_y = int(math.floor(self.y / CHUNK_SIZE))
        
        x_adjusted = self.x
        # Only apply hex offset adjustment in hex mode
        if hex_mode and chunk_y % 2 != 0:
            x_adjusted -= CHUNK_SIZE * 0.5
        
        chunk_x = int(math.floor(x_adjusted / CHUNK_SIZE))
        return (chunk_x, chunk_y)
    
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
        
        # Grid mode: True = hex offset (7 chunks), False = regular 3x3 (9 chunks)
        self.hex_mode = True
        
        # Slowmo mode: rate-limits chunk operations
        self.slowmo_mode = False
        self.slowmo_frame_counter = 0
        
        # Start player at origin (will be in chunk 0,0)
        self.player = Player(CHUNK_SIZE // 2, CHUNK_SIZE // 2)
        self.chunk_manager = ChunkManager()
        
        # Initial chunk load
        self.chunk_manager.update(*self.player.get_chunk_coords(self.hex_mode), self.hex_mode, self.slowmo_mode)
        self.last_chunk = self.player.get_chunk_coords(self.hex_mode)
        
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
            current_chunk = self.player.get_chunk_coords(self.hex_mode)
            if current_chunk != self.last_chunk:
                self.chunk_manager.update(*current_chunk, self.hex_mode, self.slowmo_mode)
                self.last_chunk = current_chunk
    
    def toggle_mode(self):
        """Toggle between hex offset mode and regular 3x3 grid."""
        self.hex_mode = not self.hex_mode
        mode_name = "Hex Offset (7 chunks)" if self.hex_mode else "Regular 3x3 (9 chunks)"
        print(f"[MODE] Switched to: {mode_name}")
        
        # Recalculate chunk position and reload chunks for new mode
        self.last_chunk = self.player.get_chunk_coords(self.hex_mode)
        self.chunk_manager.update(*self.last_chunk, self.hex_mode, self.slowmo_mode)
    
    def toggle_slowmo(self):
        """Toggle slowmo mode."""
        self.slowmo_mode = not self.slowmo_mode
        self.slowmo_frame_counter = 0
        status = "ON" if self.slowmo_mode else "OFF"
        print(f"[SLOWMO] {status}")
        
        # If turning off slowmo, flush all pending operations immediately
        if not self.slowmo_mode:
            self.last_chunk = self.player.get_chunk_coords(self.hex_mode)
            self.chunk_manager.update(*self.last_chunk, self.hex_mode, False)
    
    def process_slowmo(self):
        """Handle slowmo frame counting and processing."""
        if not self.slowmo_mode:
            return
        
        self.slowmo_frame_counter += 1
        if self.slowmo_frame_counter >= SLOWMO_INTERVAL:
            self.slowmo_frame_counter = 0
            result = self.chunk_manager.process_slowmo_tick()
            if result:
                print(f"[SLOWMO] {result}")
    
    def chunk_world_pos(self, chunk_x: int, chunk_y: int) -> tuple[float, float]:
        """Get the world position of a chunk's top-left corner."""
        world_x = chunk_x * CHUNK_SIZE
        # Only apply hex offset in hex mode
        if self.hex_mode and chunk_y % 2 != 0:
            world_x += CHUNK_SIZE * 0.5
        world_y = chunk_y * CHUNK_SIZE
        return (world_x, world_y)
    
    def world_to_screen(self, world_x: float, world_y: float) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates (camera follows player)."""
        screen_x = world_x - self.player.x + self.camera_offset[0]
        screen_y = world_y - self.player.y + self.camera_offset[1]
        return (int(screen_x), int(screen_y))
    
    def render_chunk(self, chunk: Chunk, pending_unload: bool = False):
        """Render a single chunk with its coordinates and hash."""
        # Calculate chunk's world position (with hex offset)
        world_x, world_y = self.chunk_world_pos(chunk.x, chunk.y)
        screen_x, screen_y = self.world_to_screen(world_x, world_y)
        
        # Choose fill color based on state
        fill_color = CHUNK_PENDING_UNLOAD if pending_unload else CHUNK_FILL
        border_color = (120, 60, 60) if pending_unload else CHUNK_BORDER
        
        # Draw chunk rectangle
        rect = pygame.Rect(screen_x, screen_y, CHUNK_SIZE, CHUNK_SIZE)
        pygame.draw.rect(self.screen, fill_color, rect)
        pygame.draw.rect(self.screen, border_color, rect, 2)
        
        # Render coordinate text
        coord_text = f"({chunk.x}, {chunk.y})"
        coord_surface = self.font.render(coord_text, True, COORD_COLOR)
        coord_rect = coord_surface.get_rect(center=(screen_x + CHUNK_SIZE//2, screen_y + CHUNK_SIZE//2 - 10))
        self.screen.blit(coord_surface, coord_rect)
        
        # Render hash text
        hash_surface = self.font.render(chunk.hash_id, True, HASH_COLOR)
        hash_rect = hash_surface.get_rect(center=(screen_x + CHUNK_SIZE//2, screen_y + CHUNK_SIZE//2 + 10))
        self.screen.blit(hash_surface, hash_rect)
        
        # Show "UNLOAD" label if pending
        if pending_unload:
            label = self.font.render("UNLOAD", True, (255, 100, 100))
            label_rect = label.get_rect(center=(screen_x + CHUNK_SIZE//2, screen_y + CHUNK_SIZE//2 + 30))
            self.screen.blit(label, label_rect)
    
    def render_pending_load(self, coord: tuple[int, int]):
        """Render a ghost chunk that's queued for loading."""
        world_x, world_y = self.chunk_world_pos(coord[0], coord[1])
        screen_x, screen_y = self.world_to_screen(world_x, world_y)
        
        # Draw ghost rectangle
        rect = pygame.Rect(screen_x, screen_y, CHUNK_SIZE, CHUNK_SIZE)
        pygame.draw.rect(self.screen, CHUNK_PENDING_LOAD, rect)
        pygame.draw.rect(self.screen, (60, 120, 70), rect, 2)
        
        # Show coordinate and "LOAD" label
        coord_text = f"({coord[0]}, {coord[1]})"
        coord_surface = self.font.render(coord_text, True, (100, 180, 120))
        coord_rect = coord_surface.get_rect(center=(screen_x + CHUNK_SIZE//2, screen_y + CHUNK_SIZE//2 - 5))
        self.screen.blit(coord_surface, coord_rect)
        
        label = self.font.render("LOAD", True, (100, 200, 120))
        label_rect = label.get_rect(center=(screen_x + CHUNK_SIZE//2, screen_y + CHUNK_SIZE//2 + 15))
        self.screen.blit(label, label_rect)
    
    def render_player(self):
        """Render the player circle at screen center."""
        pygame.draw.circle(self.screen, PLAYER_COLOR, self.camera_offset, PLAYER_RADIUS)
        pygame.draw.circle(self.screen, (255, 255, 255), self.camera_offset, PLAYER_RADIUS, 2)
    
    def render_hud(self):
        """Render HUD information."""
        chunk_x, chunk_y = self.player.get_chunk_coords(self.hex_mode)
        mode_name = "Hex Offset (7)" if self.hex_mode else "Regular 3x3 (9)"
        slowmo_status = f"ON ({self.chunk_manager.queue_status})" if self.slowmo_mode else "OFF"
        
        texts = [
            f"Player World Pos: ({self.player.x:.0f}, {self.player.y:.0f})",
            f"Current Chunk: ({chunk_x}, {chunk_y})",
            f"Loaded Chunks: {len(self.chunk_manager.chunks)}",
            f"Mode: {mode_name}",
            f"Slowmo: {slowmo_status}",
            "Move: WASD | 1: Toggle Mode | 2: Toggle Slowmo | ESC: Quit"
        ]
        
        for i, text in enumerate(texts):
            surface = self.font_large.render(text, True, TEXT_COLOR)
            self.screen.blit(surface, (20, 20 + i * 25))
        
        # Show slowmo progress bar
        if self.slowmo_mode:
            bar_x, bar_y = 20, 180
            bar_width, bar_height = 200, 10
            progress = self.slowmo_frame_counter / SLOWMO_INTERVAL
            
            pygame.draw.rect(self.screen, (40, 45, 55), (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(self.screen, (100, 180, 255), (bar_x, bar_y, int(bar_width * progress), bar_height))
    
    def render(self):
        """Render the entire scene."""
        self.screen.fill(BG_COLOR)
        
        # Render pending load ghosts first (so they're behind real chunks)
        if self.slowmo_mode:
            for coord in self.chunk_manager.get_pending_loads():
                self.render_pending_load(coord)
        
        # Render all loaded chunks
        for chunk in self.chunk_manager:
            pending = self.chunk_manager.is_pending_unload((chunk.x, chunk.y))
            self.render_chunk(chunk, pending_unload=pending)
        
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
                    elif event.key == pygame.K_1:
                        self.toggle_mode()
                    elif event.key == pygame.K_2:
                        self.toggle_slowmo()
            
            self.handle_input()
            self.process_slowmo()
            self.render()
            self.clock.tick(60)
        
        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()

