"""TimeWarp: a small, self-contained Pygame space shooter."""

from __future__ import annotations

import copy
import math
import random
from collections import deque
from dataclasses import dataclass

import pygame


WIDTH = 960
HEIGHT = 720
FPS = 60
HISTORY_RATE = 30
WARP_SECONDS = 5
PLAYER_SPEED = 360
BACKGROUND = (5, 8, 25)


@dataclass
class Player:
    x: float = WIDTH / 2
    y: float = HEIGHT - 92
    lives: int = 9
    stars: int = 0
    invulnerable: float = 0
    shot_cooldown: float = 0


@dataclass
class Entity:
    kind: str
    x: float
    y: float
    radius: float
    speed: float
    hp: int = 1
    phase: float = 0
    origin_x: float = 0
    fire_cooldown: float = 1.5
    angle: float = 0


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    friendly: bool
    radius: float = 4


@dataclass
class WorldSnapshot:
    elapsed: float
    player: Player
    entities: list[Entity]
    bullets: list[Bullet]
    asteroid_timer: float
    alien_timer: float
    star_timer: float
    random_state: object


class TimeWarpGame:
    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)
        self.reset()

    def reset(self) -> None:
        self.player = Player()
        self.entities: list[Entity] = []
        self.bullets: list[Bullet] = []
        self.score = 0
        self.elapsed = 0.0
        self.asteroid_timer = 1.0
        self.alien_timer = 5.0
        self.star_timer = 3.0
        self.state = "playing"
        self.paused = False
        self.replay: list[WorldSnapshot] = []
        self.replay_elapsed = 0.0
        self.history: deque[WorldSnapshot] = deque(maxlen=HISTORY_RATE * 6 + 1)
        self.tick_count = 0
        self.history.append(self._snapshot())

    def _snapshot(self) -> WorldSnapshot:
        return WorldSnapshot(
            elapsed=self.elapsed,
            player=copy.deepcopy(self.player),
            entities=copy.deepcopy(self.entities),
            bullets=copy.deepcopy(self.bullets),
            asteroid_timer=self.asteroid_timer,
            alien_timer=self.alien_timer,
            star_timer=self.star_timer,
            random_state=self.random.getstate(),
        )

    def _restore(self, snapshot: WorldSnapshot) -> None:
        lives = self.player.lives
        stars = self.player.stars
        score = self.score
        self.elapsed = snapshot.elapsed
        self.player = copy.deepcopy(snapshot.player)
        self.player.lives = lives
        self.player.stars = stars
        self.entities = copy.deepcopy(snapshot.entities)
        self.bullets = copy.deepcopy(snapshot.bullets)
        self.asteroid_timer = snapshot.asteroid_timer
        self.alien_timer = snapshot.alien_timer
        self.star_timer = snapshot.star_timer
        self.random.setstate(snapshot.random_state)
        self.score = score

    def _portal_position(self) -> tuple[float, float]:
        return (
            WIDTH / 2 + math.sin(self.elapsed * 0.65) * 245,
            155 + math.sin(self.elapsed * 0.9) * 48,
        )

    def _spawn_asteroid(self) -> None:
        radius = self.random.uniform(17, 31)
        x = self.random.uniform(radius, WIDTH - radius)
        speed = 72 + min(110, self.elapsed * 0.28) + self.random.uniform(-12, 18)
        self.entities.append(
            Entity("asteroid", x, -radius, radius, speed,
                   phase=self.random.random() * math.tau, origin_x=x,
                   angle=self.random.random() * math.tau)
        )

    def _spawn_alien(self) -> None:
        x = self.random.uniform(75, WIDTH - 75)
        speed = 75 + min(115, self.elapsed * 0.3)
        self.entities.append(
            Entity("alien", x, -30, 25, speed, hp=3,
                   phase=self.random.random() * math.tau, origin_x=x,
                   fire_cooldown=self.random.uniform(1.0, 2.0))
        )

    def _spawn_star(self) -> None:
        x = self.random.uniform(22, WIDTH - 22)
        self.entities.append(
            Entity("star", x, -15, 13, 112 + min(45, self.elapsed * 0.08))
        )

    def _shoot(self) -> None:
        player = self.player
        if player.shot_cooldown > 0:
            return
        self.bullets.append(Bullet(player.x, player.y - 22, 0, -620, True))
        player.shot_cooldown = 0.19

    def _damage_player(self) -> None:
        if self.player.invulnerable > 0:
            return
        self.player.lives -= 1
        self.player.invulnerable = 1.35
        if self.player.lives <= 0:
            self.state = "game_over"

    def _collect_star(self, entity: Entity) -> None:
        self.player.lives += 1
        self.player.stars = min(5, self.player.stars + 1)
        self.score += 100

    def _activate_warp(self) -> None:
        needed = HISTORY_RATE * WARP_SECONDS + 1
        if self.player.stars < 5 or self.replay or len(self.history) < needed:
            return
        frames = list(self.history)[-needed:]
        stats = (self.player.lives, self.score)
        self.player.stars = 0
        self._restore(frames[0])
        self.player.lives, self.score = stats
        self.replay = copy.deepcopy(frames)
        self.replay_elapsed = 0.0
        self.history.clear()
        self.history.append(self._snapshot())

    def _update_player(self, keys: pygame.key.ScancodeWrapper, dt: float) -> None:
        dx = float(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - float(
            keys[pygame.K_LEFT] or keys[pygame.K_a]
        )
        dy = float(keys[pygame.K_DOWN] or keys[pygame.K_s]) - float(
            keys[pygame.K_UP] or keys[pygame.K_w]
        )
        length = math.hypot(dx, dy)
        if length:
            dx /= length
            dy /= length
        self.player.x = min(WIDTH - 20, max(20, self.player.x + dx * PLAYER_SPEED * dt))
        self.player.y = min(HEIGHT - 58, max(62, self.player.y + dy * PLAYER_SPEED * dt))
        self.player.invulnerable = max(0, self.player.invulnerable - dt)
        self.player.shot_cooldown = max(0, self.player.shot_cooldown - dt)
        if keys[pygame.K_SPACE]:
            self._shoot()

    def _update_entities(self, dt: float) -> None:
        for entity in self.entities:
            entity.y += entity.speed * dt
            if entity.kind == "alien":
                entity.x = entity.origin_x + math.sin(
                    self.elapsed * 1.35 + entity.phase
                ) * 76
                entity.fire_cooldown -= dt
                if entity.fire_cooldown <= 0 and entity.y > 20:
                    dx = self.player.x - entity.x
                    dy = self.player.y - entity.y
                    length = max(1, math.hypot(dx, dy))
                    bullet_speed = 215 + min(105, self.elapsed * 0.18)
                    self.bullets.append(
                        Bullet(entity.x, entity.y + 17,
                               dx / length * bullet_speed,
                               dy / length * bullet_speed, False, 5)
                    )
                    entity.fire_cooldown = max(0.75, 1.8 - self.elapsed * 0.006)
            elif entity.kind == "asteroid":
                entity.x += math.sin(self.elapsed * 1.1 + entity.phase) * 18 * dt
                entity.angle += dt * 0.8
        self.entities = [
            entity for entity in self.entities
            if entity.y < HEIGHT + entity.radius + 20
        ]

    def _update_bullets(self, dt: float) -> None:
        for bullet in self.bullets:
            bullet.x += bullet.vx * dt
            bullet.y += bullet.vy * dt
        self.bullets = [
            bullet for bullet in self.bullets
            if -20 < bullet.x < WIDTH + 20 and -30 < bullet.y < HEIGHT + 30
        ]

    def _handle_collisions(self) -> None:
        player = self.player
        remaining_bullets: list[Bullet] = []
        for bullet in self.bullets:
            if bullet.friendly:
                hit = None
                for entity in self.entities:
                    if entity.kind in ("asteroid", "alien") and math.hypot(
                        bullet.x - entity.x, bullet.y - entity.y
                    ) < bullet.radius + entity.radius:
                        hit = entity
                        break
                if hit is not None:
                    hit.hp -= 1
                    if hit.hp <= 0:
                        self.entities.remove(hit)
                        self.score += 10 if hit.kind == "asteroid" else 40
                else:
                    remaining_bullets.append(bullet)
            elif player.invulnerable <= 0 and math.hypot(
                bullet.x - player.x, bullet.y - player.y
            ) < bullet.radius + 15:
                self._damage_player()
            else:
                remaining_bullets.append(bullet)
        self.bullets = remaining_bullets

        for entity in self.entities[:]:
            distance = math.hypot(player.x - entity.x, player.y - entity.y)
            if entity.kind == "star" and distance < player_radius(player) + entity.radius:
                self._collect_star(entity)
                self.entities.remove(entity)
            elif entity.kind in ("asteroid", "alien") and distance < (
                player_radius(player) + entity.radius * 0.72
            ):
                self._damage_player()
                self.entities.remove(entity)
                if self.state == "game_over":
                    return

        if player.stars >= 5:
            portal_x, portal_y = self._portal_position()
            if math.hypot(player.x - portal_x, player.y - portal_y) < 50:
                self._activate_warp()

    def update(self, keys: pygame.key.ScancodeWrapper, dt: float) -> None:
        if self.state != "playing" or self.paused:
            return
        self.elapsed += dt
        self._update_player(keys, dt)
        self.asteroid_timer -= dt
        self.alien_timer -= dt
        self.star_timer -= dt
        if self.asteroid_timer <= 0:
            self._spawn_asteroid()
            self.asteroid_timer = max(0.42, 1.35 - self.elapsed * 0.003)
        if self.alien_timer <= 0:
            self._spawn_alien()
            self.alien_timer = max(3.2, 8.5 - self.elapsed * 0.012)
        if self.star_timer <= 0:
            self._spawn_star()
            self.star_timer = self.random.uniform(5.0, 7.0)
        self._update_entities(dt)
        self._update_bullets(dt)
        self._handle_collisions()
        self.tick_count += 1
        if self.tick_count % 2 == 0:
            self.history.append(self._snapshot())
        if self.replay:
            self.replay_elapsed += dt
            if self.replay_elapsed >= (len(self.replay) - 1) / HISTORY_RATE:
                self.replay = []


def player_radius(player: Player) -> float:
    return 16


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.Font(None, 27)
        self.small_font = pygame.font.Font(None, 21)
        self.large_font = pygame.font.Font(None, 74)
        self.title_font = pygame.font.Font(None, 105)
        self.stars = [
            (random.randrange(WIDTH), random.randrange(HEIGHT), random.choice((1, 1, 2)))
            for _ in range(100)
        ]
        self.background_offset = 0.0

    def text(
        self, value: str, x: int, y: int, color: tuple[int, int, int],
        font: pygame.font.Font | None = None, centered: bool = False
    ) -> None:
        image = (font or self.font).render(value, True, color)
        rect = image.get_rect()
        if centered:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(image, rect)

    def draw_background(self, dt: float) -> None:
        self.screen.fill(BACKGROUND)
        self.background_offset = (self.background_offset + 32 * dt) % HEIGHT
        for x, y, radius in self.stars:
            draw_y = int((y + self.background_offset * (radius * 0.5 + 0.6)) % HEIGHT)
            pygame.draw.circle(self.screen, (75, 90, 130), (x, draw_y), radius)

    def draw_ship(self, target: pygame.Surface, x: float, y: float,
                  color: tuple[int, int, int]) -> None:
        points = [
            (x, y - 20), (x + 17, y + 15), (x + 5, y + 11),
            (x, y + 18), (x - 5, y + 11), (x - 17, y + 15),
        ]
        pygame.draw.polygon(target, color, points)
        pygame.draw.polygon(target, (210, 245, 255), points, 2)
        pygame.draw.polygon(
            target, (100, 220, 255),
            [(x, y - 10), (x + 5, y + 4), (x - 5, y + 4)]
        )

    def draw_entity(self, target: pygame.Surface, entity: Entity) -> None:
        x, y = int(entity.x), int(entity.y)
        if entity.kind == "asteroid":
            points = []
            for index in range(9):
                angle = entity.angle + index * math.tau / 9
                radius = entity.radius * (0.82 + 0.18 * math.sin(index * 5.1 + entity.phase))
                points.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
            pygame.draw.polygon(target, (105, 100, 125), points)
            pygame.draw.polygon(target, (183, 164, 184), points, 2)
            pygame.draw.circle(target, (75, 70, 92), (x - 5, y - 4), 5)
            pygame.draw.circle(target, (75, 70, 92), (x + 7, y + 6), 3)
        elif entity.kind == "alien":
            color = (255, 100, 125)
            points = [
                (x - 25, y - 5), (x - 12, y - 15), (x, y - 10),
                (x + 12, y - 15), (x + 25, y - 5), (x + 16, y + 7),
                (x + 10, y + 15), (x + 4, y + 8), (x - 4, y + 8),
                (x - 10, y + 15), (x - 16, y + 7),
            ]
            pygame.draw.polygon(target, color, points)
            pygame.draw.polygon(target, (255, 215, 225), points, 2)
            pygame.draw.circle(target, (255, 245, 170), (x - 8, y - 3), 3)
            pygame.draw.circle(target, (255, 245, 170), (x + 8, y - 3), 3)
            if entity.hp > 1:
                pygame.draw.rect(target, (255, 210, 220), (x - 16, y - 23, 32, 3))
        else:
            points = []
            for index in range(10):
                angle = -math.pi / 2 + index * math.pi / 5
                radius = entity.radius if index % 2 == 0 else entity.radius * 0.43
                points.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
            pygame.draw.polygon(target, (255, 225, 92), points)
            pygame.draw.polygon(target, (255, 250, 190), points, 2)

    def draw_world(self, target: pygame.Surface, snapshot: WorldSnapshot,
                   ghost: bool = False) -> None:
        for entity in snapshot.entities:
            self.draw_entity(target, entity)
        for bullet in snapshot.bullets:
            color = (95, 235, 255) if bullet.friendly else (255, 85, 110)
            pygame.draw.circle(target, color, (int(bullet.x), int(bullet.y)), int(bullet.radius))
        if ghost:
            self.draw_ship(target, snapshot.player.x, snapshot.player.y, (100, 235, 255))

    def draw_portal(self, game: TimeWarpGame) -> None:
        x, y = game._portal_position()
        pulse = 4 * math.sin(game.elapsed * 5)
        pygame.draw.circle(self.screen, (65, 238, 255), (int(x), int(y)), int(37 + pulse), 3)
        pygame.draw.circle(self.screen, (135, 95, 255), (int(x), int(y)), 25, 2)
        pygame.draw.circle(self.screen, (20, 45, 105), (int(x), int(y)), 19)
        pygame.draw.circle(self.screen, (140, 230, 255), (int(x), int(y)), 12, 2)
        self.text("FLY IN", int(x), int(y + 48), (145, 240, 255),
                  self.small_font, centered=True)

    def draw_hud(self, game: TimeWarpGame) -> None:
        minutes, seconds = divmod(int(game.elapsed), 60)
        pygame.draw.rect(self.screen, (8, 15, 40), (0, 0, WIDTH, 47))
        pygame.draw.line(self.screen, (55, 91, 145), (0, 47), (WIDTH, 47), 1)
        self.text(f"SCORE  {game.score:06d}", 20, 14, (235, 245, 255))
        self.text(f"LIVES  {game.player.lives}", 244, 14, (255, 155, 175))
        self.text(f"STARS  {game.player.stars}/5", 385, 14, (255, 225, 105))
        self.text(f"TIME  {minutes:02d}:{seconds:02d}", 545, 14, (190, 220, 255))
        if game.player.stars >= 5:
            status, color = "WARP PORTAL OPEN", (85, 240, 255)
        elif game.replay:
            status, color = "TIME ECHO", (150, 190, 255)
        else:
            status, color = "WASD / ARROWS  MOVE   SPACE  FIRE", (150, 175, 210)
        self.text(status, 735, 14, color, self.small_font)

    def draw(self, game: TimeWarpGame, dt: float) -> None:
        self.draw_background(dt)
        if game.replay:
            frame_index = min(
                len(game.replay) - 1,
                int(game.replay_elapsed * HISTORY_RATE),
            )
            echo = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            self.draw_world(echo, game.replay[frame_index], ghost=True)
            echo.set_alpha(82)
            self.screen.blit(echo, (0, 0))

        self.draw_world(self.screen, game._snapshot())
        if game.player.stars >= 5:
            self.draw_portal(game)
        if game.player.invulnerable <= 0 or int(game.elapsed * 14) % 2 == 0:
            self.draw_ship(self.screen, game.player.x, game.player.y, (90, 205, 255))
        self.draw_hud(game)

        if game.paused:
            self._draw_overlay("PAUSED", "Press P to continue")
        elif game.state == "game_over":
            self._draw_overlay("GAME OVER", "Press ENTER to play again  |  ESC to quit")

    def _draw_overlay(self, title: str, subtitle: str) -> None:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((3, 5, 19, 190))
        self.screen.blit(shade, (0, 0))
        self.text(title, WIDTH // 2, HEIGHT // 2 - 38, (130, 235, 255),
                  self.large_font, centered=True)
        self.text(subtitle, WIDTH // 2, HEIGHT // 2 + 25, (225, 235, 255),
                  self.font, centered=True)

    def draw_title(self) -> None:
        self.draw_background(1 / FPS)
        self.text("TIMEWARP", WIDTH // 2, 195, (105, 220, 255),
                  self.title_font, centered=True)
        self.text("A SPACE-TIME ARCADE RUN", WIDTH // 2, 255,
                  (255, 225, 115), self.font, centered=True)
        self.text("Dodge asteroids. Fight alien ships. Rewrite your last five seconds.",
                  WIDTH // 2, 335, (205, 220, 245), self.font, centered=True)
        self.text("Move: WASD or Arrow Keys     Fire: SPACE     Pause: P",
                  WIDTH // 2, 390, (175, 200, 230), self.font, centered=True)
        self.text("Collect five stars to open a portal, then fly into it to rewind.",
                  WIDTH // 2, 425, (125, 235, 255), self.font, centered=True)
        self.text("Every star also grants one extra life. You start with nine.",
                  WIDTH // 2, 455, (255, 220, 120), self.font, centered=True)
        self.text("Press ENTER to launch", WIDTH // 2, 545, (255, 255, 255),
                  self.large_font, centered=True)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("TimeWarp")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    game = TimeWarpGame()
    on_title = True
    accumulator = 0.0
    fixed_dt = 1 / FPS
    running = True

    while running:
        frame_dt = min(clock.tick(FPS) / 1000, 0.05)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif on_title and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    game.reset()
                    on_title = False
                elif game.state == "game_over" and event.key in (
                    pygame.K_RETURN, pygame.K_KP_ENTER
                ):
                    game.reset()
                elif not on_title and game.state == "playing" and event.key == pygame.K_p:
                    game.paused = not game.paused

        if on_title:
            renderer.draw_title()
        else:
            accumulator += frame_dt
            keys = pygame.key.get_pressed()
            while accumulator >= fixed_dt:
                game.update(keys, fixed_dt)
                accumulator -= fixed_dt
            renderer.draw(game, frame_dt)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
