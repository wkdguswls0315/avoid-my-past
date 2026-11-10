import ctypes
from bisect import bisect_right
from math import atan2, cos, hypot, pi, sin
from os import environ
from pathlib import Path
from time import perf_counter
from typing import NamedTuple

import pico2d
import pico2d.pico2d as pico2d_core
from pico2d import (
    Font,
    Image,
    SDL_KEYDOWN,
    SDL_KEYUP,
    SDL_QUIT,
    SDLK_DOWN,
    SDLK_ESCAPE,
    SDLK_LEFT,
    SDLK_KP_ENTER,
    SDLK_RETURN,
    SDLK_RIGHT,
    SDLK_UP,
    SDLK_a,
    SDLK_d,
    SDLK_s,
    SDLK_w,
    SDL_BUTTON_LEFT,
    SDL_MOUSEBUTTONDOWN,
    SDL_MOUSEMOTION,
    Mix_Volume,
    Mix_VolumeMusic,
    close_canvas,
    clear_canvas,
    draw_circle,
    draw_line,
    draw_rectangle,
    get_events,
    load_font,
    load_image,
    open_canvas,
    update_canvas,
)


SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
MENU_BUTTON_CENTER_X = 610
MENU_BUTTON_HALF_WIDTH = 290
MENU_BUTTON_HALF_HEIGHT = 34
MENU_ITEMS = (("게임 시작", 500), ("종료", 380), ("설정", 260))
SETTINGS_ITEM_Y = (510, 390, 270)
PAUSE_ITEMS = (("설정", 430), ("종료", 310))
PAUSE_ITEM_Y = tuple(y for _, y in PAUSE_ITEMS)
MAP = (
    "#########################",
    "#.......................#",
    "#.....BBBB..............#",
    "#.......................#",
    "#.................KK....#",
    "#...KK.......O..........#",
    "#............O..........#",
    "#............O..........#",
    "#.......................#",
    "#.................CCCC..#",
    "#........JJ.............#",
    "#.......................#",
    "#.......................#",
    "#########################",
)
TILE_WIDTH = SCREEN_WIDTH / len(MAP[0])
TILE_HEIGHT = SCREEN_HEIGHT / len(MAP)
MAP_OFFSET_X = 0
MAP_OFFSET_Y = 0
START_TILE = (2, 12)
GOAL_TILE = (22, 1)
SOLID_TILES = "#OBCKJ"
PROP_SPRITES = {"B": (21, 19), "C": (22, 19), "J": (23, 19), "K": (21, 18)}
LAMP_TILES = ((3, 11, 340), (8, 3, 340), (11, 8, 365),
              (14, 4, 340), (20, 8, 355), (21, 2, 335))
PLAYER_START = (
    (START_TILE[0] + 0.5) * TILE_WIDTH,
    (len(MAP) - START_TILE[1] - 0.5) * TILE_HEIGHT,
)
PLAYER_RADIUS = 13
PLAYER_SPEED = 205
START_SAFE_RADIUS = 60
GHOST_HIT_RADIUS = 22
FIRST_GHOST_DELAY = 1.0
GHOST_INTERVAL = 1.25
# 열쇠가 저장고의 서로 다른 구역에 나타나도록 배치한다.
ROUNDS = (
    ((17, 11), 54),
    ((4, 3), 52),
    ((15, 4), 50),
    ((5, 8), 50),
    ((21, 6), 48),
)
SPRITE_FRAME_SIZE = 320
SPRITE_ROWS = {
    "down": 3 * SPRITE_FRAME_SIZE,
    "left": 2 * SPRITE_FRAME_SIZE,
    "right": SPRITE_FRAME_SIZE,
    "up": 0,
}
KEY_DIRECTIONS = {
    SDLK_UP: (0, 1),
    SDLK_w: (0, 1),
    SDLK_DOWN: (0, -1),
    SDLK_s: (0, -1),
    SDLK_LEFT: (-1, 0),
    SDLK_a: (-1, 0),
    SDLK_RIGHT: (1, 0),
    SDLK_d: (1, 0),
}


def is_blocked(x: float, y: float, radius: float = PLAYER_RADIUS) -> bool:
    """Return whether the player's collision box overlaps a wall or obstacle."""
    for corner_x in (x - radius, x + radius):
        for corner_y in (y - radius, y + radius):
            column = int((corner_x - MAP_OFFSET_X) // TILE_WIDTH)
            row_from_bottom = int((corner_y - MAP_OFFSET_Y) // TILE_HEIGHT)
            row = len(MAP) - 1 - row_from_bottom
            if not (0 <= row < len(MAP) and 0 <= column < len(MAP[row])):
                return True
            if MAP[row][column] in SOLID_TILES:
                return True
    return False


def move_player(
    x: float,
    y: float,
    move_x: int,
    move_y: int,
    delta_time: float,
) -> tuple[float, float]:
    """Move smoothly while keeping the player inside walkable map tiles."""
    if move_x == 0 and move_y == 0:
        return x, y

    direction_length = (move_x**2 + move_y**2) ** 0.5
    distance = PLAYER_SPEED * delta_time / direction_length
    next_x = x + move_x * distance
    next_y = y + move_y * distance

    if not is_blocked(next_x, y):
        x = next_x
    if not is_blocked(x, next_y):
        y = next_y
    return x, y


def mouse_event_to_canvas_position(x: int, y: int) -> tuple[float, float]:
    """Convert Pico2D logical mouse-event coordinates to the canvas origin."""
    return float(x), SCREEN_HEIGHT - y


def menu_item_at(screen: str, x: float, y: float) -> int | None:
    item_positions = {
        "menu": tuple(item_y for _, item_y in MENU_ITEMS),
        "settings": SETTINGS_ITEM_Y,
        "pause": PAUSE_ITEM_Y,
    }[screen]
    for index, center_y in enumerate(item_positions):
        if (
            MENU_BUTTON_CENTER_X - MENU_BUTTON_HALF_WIDTH <= x
            <= MENU_BUTTON_CENTER_X + MENU_BUTTON_HALF_WIDTH
            and center_y - MENU_BUTTON_HALF_HEIGHT <= y
            <= center_y + MENU_BUTTON_HALF_HEIGHT
        ):
            return index
    return None


def tile_origin(column: int, row: int) -> tuple[float, float]:
    return (
        MAP_OFFSET_X + column * TILE_WIDTH,
        MAP_OFFSET_Y + (len(MAP) - row - 1) * TILE_HEIGHT,
    )


def tile_center(column: int, row: int) -> tuple[float, float]:
    x, y = tile_origin(column, row)
    return x + TILE_WIDTH / 2, y + TILE_HEIGHT / 2


def fill(x: float, y: float, width: float, height: float, color: tuple[int, ...]) -> None:
    draw_rectangle(
        int(x), int(y), int(x + width) - 1, int(y + height) - 1, *color, filled=True,
    )


def draw_tile(column: int, row: int, tile: str) -> None:
    x, y = tile_origin(column, row)
    variant = (column * 19 + row * 23) % 9
    fill(x, y, TILE_WIDTH, TILE_HEIGHT, (28, 29, 35))

    if tile in "#O":
        fill(x, y + 9, TILE_WIDTH, TILE_HEIGHT - 9, (67, 66, 69))
        fill(x + 2, y + 2, 60, 10, (45, 42, 47))
        for course in range(3):
            base = y + 12 + 16 * course
            edges = (2, 24, 62) if (row + course) % 2 else (2, 39, 62)
            for left, right in zip(edges, edges[1:]):
                value = 82 + (variant + left + course * 3) % 13
                fill(x + left, base, right - left - 2, 13, (value, value - 2, value))
                fill(x + left, base + 11, right - left - 2, 2,
                     (value + 16, value + 13, value + 12))
        fill(x, y + 59, 64, 5, (116, 108, 103))
        if tile == "O":
            for brace in (12, 50):
                fill(x + brace, y + 2, 3, 58, (54, 44, 37))
        return

    # 줄눈을 어긋나게 놓고 타일마다 석재 색과 흠집을 조금씩 다르게 만든다.
    for course in range(2):
        base = y + 32 * course
        edges = (0, 21, 64) if (row + course) % 2 else (0, 43, 64)
        for left, right in zip(edges, edges[1:]):
            value = 65 + (variant + left + 2 * course) % 13
            if row < 6 and column < 10:
                color = (value + 4, value - 3, value - 3)
            elif column > 15:
                color = (value + 1, value, value + 3)
            else:
                color = (value, value - 2, value + 1)
            fill(x + left + 1, base + 1, right - left - 2, 30, color)
            fill(x + left + 2, base + 29, right - left - 4, 2,
                 (value + 13, value + 10, value + 10))
            fill(x + left + 2, base + 1, right - left - 4, 3,
                 (value - 13, value - 14, value - 12))
            mark_x = x + left + 4 + variant % 5
            fill(mark_x, base + 9 + variant, 3 + variant % 4, 2,
                 (value - 8, value - 9, value - 6))


def draw_prop(props: Image, column: int, row: int, tile: str) -> None:
    x, y = tile_center(column, row)
    source_x, source_y = PROP_SPRITES[tile]
    # 오브젝트의 받침을 타일에 맞춰, 충돌 범위를 화면에서 알아볼 수 있게 한다.
    fill(x - 31, y - 29, 62, 56, (38, 34, 38))
    fill(x - 29, y - 26, 58, 4, (122, 99, 70))
    props.clip_draw(source_x * 16, props.h - (source_y + 1) * 16, 16, 16, x, y + 2, 56, 56)


def draw_cellar_details() -> None:
    # 벽 안쪽에 돌기둥과 황동 장식을 붙여 오래된 저택의 기초를 표현한다.
    for column in (3, 11, 17, 21):
        for row in (0, len(MAP) - 1):
            x, y = tile_origin(column, row)
            fill(x + 13, y + 3, 38, TILE_HEIGHT - 6, (42, 39, 43))
            fill(x + 16, y + 4, 31, TILE_HEIGHT - 9, (101, 96, 94))
            fill(x + 17, y + 8, 5, TILE_HEIGHT - 16, (137, 126, 118))
            for cap in (4, 52):
                fill(x + 12, y + cap, 40, 8, (120, 110, 103))
                fill(x + 12, y + cap + 6, 40, 2, (153, 140, 127))
            draw_circle(x + 32, y + 33, 5, 177, 131, 78)

    # 철문으로 이어지는 낡은 러너와 저장고 중앙의 석재 테두리.
    aisle_x, aisle_y = tile_origin(11, 11)
    for side in (6, 121):
        fill(aisle_x + side, aisle_y + 6, 2, TILE_HEIGHT * 10 - 12, (115, 103, 89))
        for mark in range(10):
            fill(aisle_x + side - 2, aisle_y + 29 + mark * TILE_HEIGHT, 6, 6, (143, 123, 96))
    carpet_x, carpet_y = tile_origin(22, 7)
    carpet_height = TILE_HEIGHT * 6 - 14
    fill(carpet_x + 9, carpet_y + 7, 46, carpet_height, (57, 37, 42))
    fill(carpet_x + 14, carpet_y + 12, 36, carpet_height - 10, (95, 49, 53))
    for side in (16, 46):
        fill(carpet_x + side, carpet_y + 12, 2, carpet_height - 10, (141, 100, 64))
    for index in range(6):
        x, y = carpet_x + 32, carpet_y + 36 + index * TILE_HEIGHT
        draw_line(x - 8, y, x, y + 10, 130, 85, 64)
        draw_line(x, y + 10, x + 8, y, 130, 85, 64)
        draw_line(x + 8, y, x, y - 10, 130, 85, 64)
        draw_line(x, y - 10, x - 8, y, 130, 85, 64)

    crest_x, crest_y = tile_center(7, 7)
    draw_circle(crest_x, crest_y, 39, 62, 54, 58, filled=True)
    draw_circle(crest_x, crest_y, 38, 147, 122, 89)
    draw_circle(crest_x, crest_y, 32, 108, 93, 73)
    vertices = [(crest_x - 14, crest_y + 12), (crest_x + 14, crest_y + 12),
                (crest_x + 11, crest_y - 5), (crest_x, crest_y - 16),
                (crest_x - 11, crest_y - 5)]
    for start, end in zip(vertices, vertices[1:] + vertices[:1]):
        draw_line(*start, *end, 163, 129, 85)
    fill(crest_x - 2, crest_y - 6, 4, 15, (162, 129, 84))
    fill(crest_x - 8, crest_y + 1, 16, 3, (162, 129, 84))

    for column, row in ((7, 10), (15, 7), (19, 3)):
        x, y = tile_center(column, row)
        fill(x - 14, y - 14, 28, 28, (93, 86, 81))
        fill(x - 12, y - 12, 24, 24, (34, 34, 37))
        for dx in range(-9, 10, 5):
            fill(x + dx, y - 10, 2, 20, (106, 100, 96))
    for column, row in ((2, 5), (9, 6), (15, 9), (21, 7)):
        x, y = tile_center(column, row)
        draw_rectangle(x - 19, y - 19, x + 19, y + 19, 106, 95, 81)
        for dx, dy in ((-15, -15), (15, -15), (-15, 15), (15, 15)):
            fill(x + dx - 2, y + dy - 2, 4, 4, (142, 124, 89))
        draw_line(x - 9, y, x + 9, y, 99, 87, 77)
        draw_line(x, y - 9, x, y + 9, 99, 87, 77)
    # 지하실로 내려온 돌계단과 위층으로 이어지는 철문.
    x, y = PLAYER_START
    for index in range(24):
        angle = index * pi / 12
        ends = [(x + cos(a) * START_SAFE_RADIUS, y + sin(a) * START_SAFE_RADIUS)
                for a in (angle, angle + pi / 20)]
        if all(not is_blocked(px, py, 1) for px, py in ends):
            draw_line(*ends[0], *ends[1], 124, 105, 74)
    fill(x - 22, y - 25, 44, 47, (49, 49, 55))
    for step in range(5):
        level = y - 21 + 8 * step
        fill(x - 20, level, 40, 7, (86 + step * 6, 83 + step * 5, 82 + step * 4))
        fill(x - 20, level, 40, 2, (52, 51, 56))
    x, y = tile_center(*GOAL_TILE)
    fill(x - 29, y - 26, 58, 54, (127, 116, 103))
    fill(x - 24, y - 22, 48, 46, (53, 53, 57))
    for dx in range(-19, 21, 10):
        fill(x + dx, y - 18, 7, 39, (107, 105, 110))
        fill(x + dx, y - 18, 2, 39, (135, 132, 134))
    for dy in (-14, 13):
        fill(x - 23, y + dy, 46, 5, (61, 61, 63))
    draw_circle(x + 12, y, 4, 233, 176, 94)
    fill(x - 29, y - 28, 58, 5, (167, 148, 116))


def draw_lantern(x: float, y: float) -> None:
    draw_circle(x + 3, y - 2, 13, 49, 38, 32, filled=True)
    fill(x - 7, y - 8, 15, 17, (98, 64, 37))
    fill(x - 5, y - 5, 11, 12, (241, 147, 62))
    fill(x - 2, y - 4, 5, 10, (255, 239, 161))
    fill(x - 8, y + 7, 17, 3, (174, 115, 55))
    fill(x - 8, y - 9, 17, 3, (174, 115, 55))


class Lamp(NamedTuple):
    x: float
    y: float
    reach: float


def ray_distance(x, y, dx, dy, limit, walls) -> float:
    """Return the distance along a ray to the first solid tile."""
    for left, bottom, right, top in walls:
        enter, leave = 0.0, limit
        for start, direction, low, high in ((x, dx, left, right), (y, dy, bottom, top)):
            if abs(direction) < 1e-9:
                if not low <= start <= high:
                    break
                continue
            t1, t2 = (low - start) / direction, (high - start) / direction
            enter = max(enter, min(t1, t2))
            leave = min(leave, max(t1, t2))
            if leave < enter:
                break
        else:
            limit = enter
    return limit


def draw_mesh(points, indices) -> None:
    p = pico2d
    vertices = (p.SDL_Vertex * len(points))(*(
        p.SDL_Vertex(p.SDL_FPoint(x, SCREEN_HEIGHT - y), p.SDL_Color(*color), p.SDL_FPoint())
        for x, y, color in points
    ))
    index_type = p.SDL_RenderGeometry.argtypes[4]._type_
    triangles = (index_type * len(indices))(*indices)
    p.SDL_RenderGeometry(pico2d_core.renderer, None, vertices, len(vertices), triangles, len(triangles))


class Cellar:
    def __init__(self, props: Image) -> None:
        self.props = props
        self.lamps = [Lamp(*tile_center(column, row), reach) for column, row, reach in LAMP_TILES]
        self.walls = []
        for row, tiles in enumerate(MAP):
            for column, tile in enumerate(tiles):
                if tile in SOLID_TILES:
                    x, y = tile_origin(column, row)
                    self.walls.append((x, y, x + TILE_WIDTH, y + TILE_HEIGHT))
        self.floor = self.build_texture(self.draw_floor, pico2d.SDL_BLENDMODE_NONE)
        self.lighting = self.build_texture(self.draw_lighting, pico2d.SDL_BLENDMODE_MOD)

    @staticmethod
    def build_texture(draw, blend_mode):
        p, renderer = pico2d, pico2d_core.renderer
        texture = p.SDL_CreateTexture(
            renderer, p.SDL_PIXELFORMAT_RGBA8888, p.SDL_TEXTUREACCESS_TARGET,
            SCREEN_WIDTH, SCREEN_HEIGHT,
        )
        if not texture:
            raise RuntimeError(f"Could not create the cellar texture: {sdl_error_message()}")
        if p.SDL_SetRenderTarget(renderer, texture) != 0:
            p.SDL_DestroyTexture(texture)
            raise RuntimeError(f"Could not draw the cellar texture: {sdl_error_message()}")
        try:
            draw()
        finally:
            p.SDL_SetRenderTarget(renderer, None)
            p.SDL_SetRenderDrawBlendMode(renderer, p.SDL_BLENDMODE_BLEND)
        p.SDL_SetTextureBlendMode(texture, blend_mode)
        return texture

    def draw_floor(self) -> None:
        clear_canvas()
        for row, tiles in enumerate(MAP):
            for column, tile in enumerate(tiles):
                draw_tile(column, row, tile)
        draw_cellar_details()
        for row, tiles in enumerate(MAP):
            for column, tile in enumerate(tiles):
                if tile in PROP_SPRITES:
                    draw_prop(self.props, column, row, tile)
        for lamp in self.lamps:
            draw_lantern(lamp.x, lamp.y)

    def draw_lighting(self) -> None:
        p, renderer = pico2d, pico2d_core.renderer
        p.SDL_SetRenderDrawColor(renderer, 126, 129, 153, 255)
        p.SDL_RenderClear(renderer)
        p.SDL_SetRenderDrawBlendMode(renderer, p.SDL_BLENDMODE_ADD)
        for lamp in self.lamps:
            self.draw_lamp_light(lamp)

    def draw_lamp_light(self, lamp: Lamp) -> None:
        # 장애물 모서리의 양옆으로 광선을 쏴 좁은 그림자 경계도 놓치지 않는다.
        nearby = [wall for wall in self.walls
                  if wall[0] < lamp.x + lamp.reach and wall[2] > lamp.x - lamp.reach
                  and wall[1] < lamp.y + lamp.reach and wall[3] > lamp.y - lamp.reach]
        angles = {i * pi / 64 for i in range(-64, 64)}
        for left, bottom, right, top in nearby:
            for x in (left, right):
                for y in (bottom, top):
                    angle = atan2(y - lamp.y, x - lamp.x)
                    angles.update((angle - 0.001, angle + 0.001))
        points = [(lamp.x, lamp.y, (153, 126, 87, 255))]
        ring_count = 5
        for angle in sorted(angles):
            dx, dy = cos(angle), sin(angle)
            wall_distance = ray_distance(lamp.x, lamp.y, dx, dy, lamp.reach, nearby)
            # 부딪힌 면에도 빛이 조금 닿도록 돌 표면 안쪽까지 짧게 확장한다.
            limit = min(lamp.reach, wall_distance + 9)
            for ring in range(1, ring_count + 1):
                distance = limit * ring / ring_count
                strength = (1 - distance / lamp.reach) ** 1.6
                color = (*[int(channel * strength) for channel in (153, 126, 87)], 255)
                points.append((lamp.x + dx * distance, lamp.y + dy * distance, color))
        indices = []
        for index in range(len(angles)):
            first = 1 + index * ring_count
            second = 1 + ((index + 1) % len(angles)) * ring_count
            indices.extend((0, first, second))
            for ring in range(ring_count - 1):
                a, b = first + ring, second + ring
                indices.extend((a, a + 1, b, b, a + 1, b + 1))
        draw_mesh(points, indices)

    def draw_shadows(self, x: float, y: float) -> None:
        draw_circle(x, y - 10, 10, 10, 9, 13, 125, filled=True)
        for lamp in self.lamps:
            dx, dy = x - lamp.x, y - 8 - lamp.y
            distance = hypot(dx, dy)
            if not 10 < distance < lamp.reach * 0.8:
                continue
            dx, dy = dx / distance, dy / distance
            if ray_distance(lamp.x, lamp.y, dx, dy, distance, self.walls) < distance - 1:
                continue
            length = min(17 + distance * 0.18, 64)
            length = ray_distance(x, y - 8, dx, dy, length, self.walls)
            if length < 5:
                continue
            opacity = int(145 * (1 - distance / lamp.reach))
            near, far = (8, 12)
            points = [
                (x - dy * near, y - 8 + dx * near, (12, 9, 13, opacity)),
                (x + dy * near, y - 8 - dx * near, (12, 9, 13, opacity)),
                (x + dx * length + dy * far, y - 8 + dy * length - dx * far, (12, 9, 13, 0)),
                (x + dx * length - dy * far, y - 8 + dy * length + dx * far, (12, 9, 13, 0)),
            ]
            draw_mesh(points, (0, 1, 2, 0, 2, 3))

    def draw_background(self) -> None:
        pico2d.SDL_RenderCopy(pico2d_core.renderer, self.floor, None, None)

    def apply_lighting(self) -> None:
        pico2d.SDL_RenderCopy(pico2d_core.renderer, self.lighting, None, None)

    def draw_lamp_glints(self, elapsed: float) -> None:
        for index, lamp in enumerate(self.lamps):
            phase = elapsed * 5 + index * 1.9
            glow = int(28 + 12 * sin(phase) + 7 * sin(phase * 2.2))
            draw_circle(lamp.x, lamp.y, 14, 255, 161, 66, glow, filled=True)
            draw_circle(lamp.x, lamp.y, 5, 255, 230, 154, 85 + glow, filled=True)
            for mote in range(3):
                height = (elapsed * (8 + mote) + 20 * mote + index * 8) % 64
                x = lamp.x + 19 * sin(height / 15 + mote * 2.4)
                alpha = int(100 * sin(pi * height / 64))
                fill(x, lamp.y + height, 2, 2, (240, 198, 128, alpha))

    def close(self) -> None:
        pico2d.SDL_DestroyTexture(self.lighting)
        pico2d.SDL_DestroyTexture(self.floor)


def draw_player(sprite: Image, x: float, y: float, facing: str, frame: int) -> None:
    sprite.clip_draw(
        frame * SPRITE_FRAME_SIZE, SPRITE_ROWS[facing],
        SPRITE_FRAME_SIZE, SPRITE_FRAME_SIZE, x, y, TILE_WIDTH, TILE_HEIGHT,
    )


class MovementSample(NamedTuple):
    elapsed: float
    x: float
    y: float
    facing: str
    frame: int


def replay_at(route: list[MovementSample], elapsed: float) -> MovementSample | None:
    if not route or not 0.0 <= elapsed < route[-1].elapsed:
        return None
    index = bisect_right(route, elapsed, key=lambda sample: sample.elapsed) - 1
    start, end = route[index], route[index + 1]
    fraction = (elapsed - start.elapsed) / (end.elapsed - start.elapsed)
    return MovementSample(
        elapsed,
        start.x + (end.x - start.x) * fraction,
        start.y + (end.y - start.y) * fraction,
        start.facing,
        start.frame,
    )


class CellarRun:
    def __init__(self) -> None:
        self.routes: list[list[MovementSample]] = []
        self.reset()

    @property
    def round_number(self) -> int:
        return min(len(self.routes) + 1, len(ROUNDS))

    def reset(self, notice: str = "") -> None:
        self.routes.clear()
        self.begin_round(notice)

    def begin_round(self, notice: str = "") -> None:
        self.key_tile, self.time_limit = ROUNDS[self.round_number - 1]
        self.x, self.y = PLAYER_START
        self.facing, self.frame = "down", 0
        self.elapsed = self.animation_time = 0.0
        self.has_key = False
        self.recording = [self.sample()]
        self.ghosts: list[MovementSample] = []
        self.notice, self.notice_until = notice, 3.0

    def sample(self) -> MovementSample:
        return MovementSample(self.elapsed, self.x, self.y, self.facing, self.frame)

    def update(self, move_x: int, move_y: int, delta_time: float) -> str:
        if delta_time <= 0.0:
            return "playing"
        self.elapsed += delta_time
        previous = self.x, self.y
        self.x, self.y = move_player(self.x, self.y, move_x, move_y, delta_time)
        self.frame = 0
        if (self.x, self.y) != previous:
            if abs(move_x) > abs(move_y):
                self.facing = "right" if move_x > 0 else "left"
            else:
                self.facing = "up" if move_y > 0 else "down"
            self.animation_time += delta_time
            self.frame = int(self.animation_time * 8) % 4
        self.recording.append(self.sample())
        self.ghosts = [
            ghost for index, route in enumerate(self.routes)
            if (ghost := replay_at(route, self.elapsed - FIRST_GHOST_DELAY - index * GHOST_INTERVAL))
            is not None
        ]
        # 같은 위치에서 출발한 기록이 겹쳐도 계단 앞에서는 안전하다.
        if hypot(self.x - PLAYER_START[0], self.y - PLAYER_START[1]) > START_SAFE_RADIUS:
            for ghost in self.ghosts:
                if hypot(self.x - ghost.x, self.y - ghost.y) < GHOST_HIT_RADIUS:
                    self.reset("분신과 접촉했습니다. 1라운드부터 다시 시작합니다.")
                    return "reset"
        if self.elapsed >= self.time_limit:
            self.reset("시간이 끝났습니다. 1라운드부터 다시 시작합니다.")
            return "reset"
        key_x, key_y = tile_center(*self.key_tile)
        if not self.has_key and hypot(self.x - key_x, self.y - key_y) < 24:
            self.has_key = True
            self.notice = "열쇠를 찾았습니다. 북동쪽 철문으로 가세요."
            self.notice_until = self.elapsed + 2.5
        door_x, door_y = tile_center(*GOAL_TILE)
        if self.has_key and hypot(self.x - door_x, self.y - door_y) < 25:
            self.routes.append(self.recording)
            if len(self.routes) == len(ROUNDS):
                return "clear"
            self.begin_round("새 열쇠를 찾으세요. 분신은 차례로 출발합니다.")
            return "next"
        return "playing"


def draw_ghost(sprite: Image, sample: MovementSample) -> None:
    draw_circle(sample.x, sample.y, PLAYER_RADIUS + 2, 102, 220, 240, 180)
    pico2d.SDL_SetTextureColorMod(sprite.texture, 115, 245, 255)
    sprite.opacify(0.55)
    draw_player(sprite, sample.x, sample.y, sample.facing, sample.frame)
    sprite.opacify(1.0)
    pico2d.SDL_SetTextureColorMod(sprite.texture, 255, 255, 255)


def draw_run_hud(menu_font: Font, hint_font: Font, run: CellarRun) -> None:
    fill(12, 847, 958, 44, (23, 20, 24, 236))
    draw_rectangle(12, 847, 970, 891, 133, 106, 74, filled=False)
    menu_font.draw(27, 867, "대저택 지하 저장고", (239, 209, 158))
    remaining = max(0, int(run.time_limit - run.elapsed + 0.999))
    key = "YES" if run.has_key else "NO"
    hint_font.draw(
        316, 865,
        f"ROUND {run.round_number}/{len(ROUNDS)}   TIME {remaining:02d}s   KEY {key}",
        (224, 210, 187),
    )
    hint_font.draw(736, 865, "SHADOWS", (139, 207, 212))
    for index in range(4):
        x = 832 + 30 * index
        color = (103, 224, 230) if index < len(run.ghosts) else (63, 89, 101)
        draw_circle(x, 869, 6, *color, filled=index < len(run.ghosts))
    if run.notice and run.elapsed < run.notice_until:
        fill(355, 10, 890, 45, (23, 20, 24, 230))
        draw_centered_text(menu_font, run.notice, 800, 32, (239, 209, 158))


def draw_key(x: float, y: float, elapsed: float) -> None:
    y += sin(elapsed * 3) * 4
    draw_circle(x, y, 18, 245, 176, 71, 26, filled=True)
    draw_circle(x - 8, y + 2, 7, 255, 211, 102)
    draw_line(x - 1, y + 2, x + 13, y + 2, 255, 211, 102)
    draw_line(x + 8, y + 2, x + 8, y - 4, 255, 211, 102)
    draw_line(x + 13, y + 2, x + 13, y - 6, 255, 211, 102)


def sdl_error_message() -> str:
    error = pico2d.SDL_GetError()
    if isinstance(error, bytes):
        return error.decode("utf-8", errors="replace")
    return str(error)


def set_display_mode(fullscreen: bool) -> None:
    window = pico2d_core.window
    flags = pico2d.SDL_WINDOW_FULLSCREEN_DESKTOP if fullscreen else 0
    if pico2d.SDL_SetWindowFullscreen(window, flags) != 0:
        raise RuntimeError(f"Could not change display mode: {sdl_error_message()}")

    if not fullscreen:
        pico2d.SDL_SetWindowSize(window, WINDOW_WIDTH, WINDOW_HEIGHT)
        pico2d.SDL_SetWindowPosition(
            window, pico2d.SDL_WINDOWPOS_CENTERED, pico2d.SDL_WINDOWPOS_CENTERED
        )

    if pico2d.SDL_RenderSetLogicalSize(
        pico2d_core.renderer, SCREEN_WIDTH, SCREEN_HEIGHT
    ) != 0:
        raise RuntimeError(f"Could not scale the game canvas: {sdl_error_message()}")


def set_sound_enabled(enabled: bool) -> None:
    if pico2d_core.audio_on:
        volume = 128 if enabled else 0
        Mix_Volume(-1, volume)
        Mix_VolumeMusic(volume)


def draw_centered_text(
    font: Font,
    text: str,
    center_x: float,
    y: float,
    color: tuple[int, int, int],
) -> None:
    text_width = ctypes.c_int()
    text_height = ctypes.c_int()
    result = pico2d.TTF_SizeUTF8(
        font.font,
        text.encode("utf-8"),
        ctypes.byref(text_width),
        ctypes.byref(text_height),
    )
    if result != 0:
        raise RuntimeError(f"Could not measure menu text: {sdl_error_message()}")
    font.draw(center_x - text_width.value / 2, y, text, color)


def draw_menu_button(
    font: Font,
    label: str,
    y: float,
    selected: bool,
    center_x: float,
) -> None:
    left = center_x - MENU_BUTTON_HALF_WIDTH
    right = center_x + MENU_BUTTON_HALF_WIDTH
    bottom = y - MENU_BUTTON_HALF_HEIGHT
    top = y + MENU_BUTTON_HALF_HEIGHT
    draw_rectangle(left, bottom, right, top, 15, 29, 44, filled=True)
    if selected:
        draw_rectangle(left, bottom, right, top, 78, 148, 151, filled=False)
        draw_rectangle(left + 3, bottom + 3, right - 3, top - 3, 43, 74, 84, filled=False)
        draw_rectangle(left + 12, bottom + 12, left + 16, top - 12, 208, 171, 106, filled=True)
    else:
        draw_rectangle(left, bottom, right, top, 42, 63, 76, filled=False)

    color = (239, 222, 186) if selected else (171, 186, 197)
    draw_centered_text(font, label, center_x, y, color)


def draw_menu_background(sprite: Image) -> None:
    clear_canvas()
    draw_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 10, 19, 34, filled=True)
    for y, color in (
        (520, (12, 24, 40)),
        (620, (14, 27, 44)),
        (720, (16, 29, 47)),
        (820, (19, 33, 51)),
    ):
        draw_rectangle(0, y, SCREEN_WIDTH, y + 100, *color, filled=True)

    draw_rectangle(0, 0, SCREEN_WIDTH, 169, 12, 22, 32, filled=True)
    floor_colors = ((16, 29, 39), (18, 31, 41), (20, 33, 43))
    for row, y in enumerate(range(0, 160, 40)):
        offset = 0 if row % 2 == 0 else -40
        for column, x in enumerate(range(offset, SCREEN_WIDTH, 80)):
            color = floor_colors[(row + column) % len(floor_colors)]
            draw_rectangle(x + 2, y + 2, x + 77, y + 37, *color, filled=True)

    for x, y, size in (
        (130, 780, 4), (245, 620, 3), (370, 835, 5), (460, 710, 3),
        (1010, 820, 4), (1090, 650, 3), (1435, 800, 4), (1510, 590, 3),
    ):
        draw_rectangle(x, y, x + size, y + size, 116, 153, 163, filled=True)

    for x in (94, 1460):
        draw_rectangle(x, 170, x + 46, 620, 14, 27, 42, filled=True)
        draw_rectangle(x - 8, 595, x + 54, 620, 40, 61, 72, filled=True)
        draw_rectangle(x - 8, 190, x + 54, 215, 40, 61, 72, filled=True)
        draw_rectangle(x + 10, 230, x + 14, 570, 52, 79, 87, filled=True)

    portal_x, portal_y = 1260, 320
    draw_rectangle(
        portal_x - 151, portal_y - 161, portal_x + 151, portal_y + 161,
        15, 34, 47, filled=True,
    )
    draw_rectangle(
        portal_x - 143, portal_y - 153, portal_x + 143, portal_y + 153,
        70, 116, 122, filled=False,
    )
    draw_rectangle(
        portal_x - 126, portal_y - 136, portal_x + 126, portal_y + 136,
        26, 49, 59, filled=True,
    )
    draw_rectangle(
        portal_x - 108, portal_y - 119, portal_x + 108, portal_y + 118,
        11, 23, 36, filled=True,
    )
    draw_rectangle(
        portal_x - 96, portal_y - 107, portal_x + 96, portal_y + 110,
        26, 49, 59, filled=False,
    )
    draw_rectangle(
        portal_x - 71, portal_y - 119, portal_x - 66, portal_y + 92,
        90, 133, 129, filled=True,
    )
    draw_rectangle(
        portal_x + 67, portal_y - 119, portal_x + 72, portal_y + 92,
        90, 133, 129, filled=True,
    )
    draw_rectangle(
        portal_x - 127, portal_y - 151, portal_x + 127, portal_y - 145,
        120, 147, 131, filled=True,
    )
    draw_rectangle(
        portal_x - 137, portal_y - 174, portal_x + 137, portal_y - 160,
        24, 43, 55, filled=True,
    )
    draw_rectangle(0, 153, SCREEN_WIDTH, 157, 55, 87, 94, filled=True)
    draw_rectangle(0, 157, SCREEN_WIDTH, 169, 17, 32, 45, filled=True)

    sprite.clip_draw(
        0, SPRITE_ROWS["down"], SPRITE_FRAME_SIZE, SPRITE_FRAME_SIZE,
        portal_x, 237, 224, 224,
    )


def draw_menu_title(title_font: Font, subtitle_font: Font) -> None:
    draw_centered_text(
        title_font, "Avoid My Past", SCREEN_WIDTH / 2 + 3, 748, (4, 10, 18)
    )
    draw_centered_text(
        title_font, "Avoid My Past", SCREEN_WIDTH / 2, 754, (238, 221, 185)
    )
    draw_centered_text(
        subtitle_font, "A JOURNEY THROUGH TIME", SCREEN_WIDTH / 2, 691,
        (117, 153, 158),
    )
    draw_rectangle(515, 671, 721, 674, 54, 91, 98, filled=True)
    draw_rectangle(879, 671, 1085, 674, 54, 91, 98, filled=True)
    draw_rectangle(793, 667, 807, 681, 173, 144, 96, filled=True)


def draw_menu_footer(font: Font, text: str) -> None:
    left, right = 320, 900
    draw_rectangle(left, 51, right, 119, 12, 24, 36, filled=True)
    draw_rectangle(left, 51, right, 119, 42, 70, 80, filled=False)
    draw_centered_text(font, text, (left + right) / 2, 85, (115, 145, 153))


def draw_menu(
    title_font: Font,
    menu_font: Font,
    hint_font: Font,
    selected_item: int,
    sprite: Image,
) -> None:
    draw_menu_background(sprite)
    draw_menu_title(title_font, hint_font)
    for index, (label, y) in enumerate(MENU_ITEMS):
        draw_menu_button(
            menu_font, label, y, index == selected_item, MENU_BUTTON_CENTER_X
        )
    draw_menu_footer(
        hint_font, "USE  UP / DOWN  TO SELECT       ENTER  TO CONFIRM"
    )


def draw_settings(
    heading_font: Font,
    menu_font: Font,
    hint_font: Font,
    selected_item: int,
    sound_enabled: bool,
    fullscreen: bool,
    sprite: Image,
    over_game: bool,
) -> None:
    if over_game:
        draw_rectangle(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 3, 8, 15, 64, filled=True)
        draw_rectangle(320, 50, 900, 765, 12, 24, 36, 178, filled=True)
    else:
        draw_menu_background(sprite)
    draw_centered_text(
        heading_font, "설정", 610, 697, (238, 221, 185)
    )
    options = (
        f"소리   {'켜짐' if sound_enabled else '꺼짐'}",
        f"화면 모드   {'전체화면' if fullscreen else '창화면 (1280 x 720)'}",
        "돌아가기",
    )
    for index, (label, y) in enumerate(zip(options, SETTINGS_ITEM_Y)):
        draw_menu_button(
            menu_font, label, y, index == selected_item, MENU_BUTTON_CENTER_X
        )
    draw_menu_footer(
        hint_font, "LEFT / RIGHT  OR  ENTER  TO CHANGE       ESC  TO RETURN"
    )


def draw_pause_overlay(
    menu_font: Font,
    hint_font: Font,
    selected_item: int,
) -> None:
    draw_rectangle(
        0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 3, 8, 15, 64, filled=True
    )
    panel_left, panel_bottom = 320, 190
    panel_right, panel_top = 900, 630
    draw_rectangle(
        panel_left, panel_bottom, panel_right, panel_top,
        12, 24, 36, 178, filled=True,
    )
    draw_rectangle(
        panel_left, panel_bottom, panel_right, panel_top,
        75, 120, 124, filled=False,
    )
    draw_centered_text(
        menu_font, "일시정지", (panel_left + panel_right) / 2, 555,
        (238, 221, 185),
    )
    for index, (label, y) in enumerate(PAUSE_ITEMS):
        draw_menu_button(
            menu_font, label, y, index == selected_item, MENU_BUTTON_CENTER_X
        )
    draw_centered_text(
        hint_font, "ESC  TO RESUME", (panel_left + panel_right) / 2, 225,
        (115, 145, 153),
    )


def main() -> None:
    open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT)
    pico2d.SDL_SetRenderDrawBlendMode(pico2d_core.renderer, pico2d.SDL_BLENDMODE_BLEND)
    set_display_mode(fullscreen=False)
    title_font = load_font(
        str(Path(environ["WINDIR"]) / "Fonts" / "georgiab.ttf"), 68
    )
    menu_font = load_font(
        str(Path(environ["WINDIR"]) / "Fonts" / "malgunbd.ttf"), 30
    )
    heading_font = load_font(
        str(Path(environ["WINDIR"]) / "Fonts" / "malgunbd.ttf"), 46
    )
    hint_font = load_font(
        str(Path(environ["WINDIR"]) / "Fonts" / "consola.ttf"), 17
    )
    assets = Path(__file__).resolve().parents[1] / "assets"
    sprite = load_image(str(assets / "player_sprite.png"))
    props = load_image(str(assets / "cellar_props.png"))
    pico2d.SDL_SetTextureScaleMode(props.texture, pico2d.SDL_ScaleModeNearest)
    cellar = Cellar(props)
    run = CellarRun()
    held_keys: set[int] = set()
    previous_time = perf_counter()
    running = True
    screen = "menu"
    pause_menu_open = False
    selected_menu_item = 0
    selected_settings_item = 0
    selected_pause_item = 0
    sound_enabled = True
    fullscreen = False

    while running:
        current_time = perf_counter()
        delta_time = min(current_time - previous_time, 0.05)
        previous_time = current_time

        for event in get_events():
            if event.type == SDL_QUIT:
                running = False
            elif event.type == SDL_KEYDOWN:
                if event.key == SDLK_ESCAPE:
                    if screen == "settings":
                        if pause_menu_open:
                            screen = "pause"
                        else:
                            screen = "menu"
                    elif screen == "game":
                        screen = "pause"
                        pause_menu_open = True
                        held_keys.clear()
                    elif screen == "pause":
                        screen = "game"
                        pause_menu_open = False
                    elif screen == "clear":
                        screen = "menu"
                    else:
                        running = False
                elif screen == "clear" and event.key in (SDLK_RETURN, SDLK_KP_ENTER):
                    screen = "menu"
                elif screen == "game" and event.key in KEY_DIRECTIONS:
                    held_keys.add(event.key)
                elif screen == "menu" and event.key in (SDLK_UP, SDLK_w):
                    selected_menu_item = (selected_menu_item - 1) % 3
                elif screen == "menu" and event.key in (SDLK_DOWN, SDLK_s):
                    selected_menu_item = (selected_menu_item + 1) % 3
                elif screen == "pause" and event.key in (SDLK_UP, SDLK_w):
                    selected_pause_item = (selected_pause_item - 1) % len(PAUSE_ITEMS)
                elif screen == "pause" and event.key in (SDLK_DOWN, SDLK_s):
                    selected_pause_item = (selected_pause_item + 1) % len(PAUSE_ITEMS)
                elif screen == "settings" and event.key in (SDLK_UP, SDLK_w):
                    selected_settings_item = (selected_settings_item - 1) % 3
                elif screen == "settings" and event.key in (SDLK_DOWN, SDLK_s):
                    selected_settings_item = (selected_settings_item + 1) % 3
                elif screen == "menu" and event.key in (SDLK_RETURN, SDLK_KP_ENTER):
                    if selected_menu_item == 0:
                        screen = "game"
                        run.reset("열쇠를 찾아 북동쪽 철문으로 가세요.")
                        held_keys.clear()
                    elif selected_menu_item == 1:
                        running = False
                    else:
                        pause_menu_open = False
                        screen = "settings"
                elif screen == "pause" and event.key in (SDLK_RETURN, SDLK_KP_ENTER):
                    if selected_pause_item == 0:
                        pause_menu_open = True
                        screen = "settings"
                    else:
                        running = False
                elif screen == "settings" and event.key in (
                    SDLK_LEFT, SDLK_RIGHT, SDLK_RETURN, SDLK_KP_ENTER
                ):
                    if selected_settings_item == 0:
                        sound_enabled = not sound_enabled
                        set_sound_enabled(sound_enabled)
                    elif selected_settings_item == 1:
                        fullscreen = not fullscreen
                        set_display_mode(fullscreen)
                    else:
                        screen = "pause" if pause_menu_open else "menu"
            elif event.type == SDL_MOUSEMOTION and screen in ("menu", "settings"):
                mouse_x, mouse_y = mouse_event_to_canvas_position(event.x, event.y)
                hovered_item = menu_item_at(screen, mouse_x, mouse_y)
                if hovered_item is not None:
                    if screen == "menu":
                        selected_menu_item = hovered_item
                    else:
                        selected_settings_item = hovered_item
            elif event.type == SDL_MOUSEMOTION and screen == "pause":
                mouse_x, mouse_y = mouse_event_to_canvas_position(event.x, event.y)
                hovered_item = menu_item_at(screen, mouse_x, mouse_y)
                if hovered_item is not None:
                    selected_pause_item = hovered_item
            elif (
                event.type == SDL_MOUSEBUTTONDOWN
                and event.button == SDL_BUTTON_LEFT
                and screen in ("menu", "settings", "pause")
            ):
                mouse_x, mouse_y = mouse_event_to_canvas_position(event.x, event.y)
                clicked_item = menu_item_at(screen, mouse_x, mouse_y)
                if clicked_item is not None and screen == "menu":
                    selected_menu_item = clicked_item
                    if clicked_item == 0:
                        screen = "game"
                        run.reset("열쇠를 찾아 북동쪽 철문으로 가세요.")
                        held_keys.clear()
                    elif clicked_item == 1:
                        running = False
                    else:
                        pause_menu_open = False
                        screen = "settings"
                elif clicked_item is not None and screen == "pause":
                    selected_pause_item = clicked_item
                    if clicked_item == 0:
                        pause_menu_open = True
                        screen = "settings"
                    else:
                        running = False
                elif clicked_item is not None:
                    selected_settings_item = clicked_item
                    if clicked_item == 0:
                        sound_enabled = not sound_enabled
                        set_sound_enabled(sound_enabled)
                    elif clicked_item == 1:
                        fullscreen = not fullscreen
                        set_display_mode(fullscreen)
                    else:
                        screen = "pause" if pause_menu_open else "menu"
            elif event.type == SDL_KEYUP and event.key in KEY_DIRECTIONS:
                held_keys.discard(event.key)

        if screen == "game":
            move_x = sum(KEY_DIRECTIONS[key][0] for key in held_keys)
            move_y = sum(KEY_DIRECTIONS[key][1] for key in held_keys)
            result = run.update(move_x, move_y, delta_time)
            if result != "playing":
                held_keys.clear()
            if result == "clear":
                screen = "clear"

        if screen in ("game", "pause", "clear") or (screen == "settings" and pause_menu_open):
            cellar.draw_background()
            cellar.draw_shadows(run.x, run.y)
            draw_player(sprite, run.x, run.y, run.facing, run.frame)
            cellar.apply_lighting()
            cellar.draw_lamp_glints(run.elapsed)
            for ghost in run.ghosts:
                draw_ghost(sprite, ghost)
            if run.has_key:
                door_x, door_y = tile_center(*GOAL_TILE)
                fill(door_x - 20, door_y - 27, 40, 3, (108, 222, 175))
            else:
                draw_key(*tile_center(*run.key_tile), run.elapsed)
            draw_run_hud(menu_font, hint_font, run)

        if screen == "pause":
            draw_pause_overlay(menu_font, hint_font, selected_pause_item)
        elif screen == "settings":
            draw_settings(
                heading_font, menu_font, hint_font, selected_settings_item,
                sound_enabled, fullscreen, sprite, pause_menu_open,
            )
        elif screen == "menu":
            draw_menu(
                title_font, menu_font, hint_font, selected_menu_item, sprite
            )
        elif screen == "clear":
            fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (13, 11, 16, 175))
            draw_centered_text(heading_font, "지하 저장고 탈출", 800, 490, (239, 209, 158))
            draw_centered_text(menu_font, "5라운드를 모두 통과했습니다.", 800, 423, (232, 226, 213))
            draw_centered_text(hint_font, "ENTER / ESC  TO MAIN MENU", 800, 366, (205, 188, 163))
        update_canvas()

    cellar.close()
    close_canvas()


if __name__ == "__main__":
    main()
