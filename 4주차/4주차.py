import ctypes
import random
import sys
from bisect import bisect_right
from collections import deque
from math import atan2, cos, hypot, pi, sin
from os import environ
from pathlib import Path
from time import perf_counter
from typing import NamedTuple


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[1]


if getattr(sys, "frozen", False):
    _frozen_root = resource_root()
    _sdl_dll_dir = _frozen_root / "sdl2dll" / "dll"
    _pico_data_dir = _frozen_root / "pico2d" / "data"
    if _sdl_dll_dir.exists():
        environ["PYSDL2_DLL_PATH"] = str(_sdl_dll_dir)
    if _pico_data_dir.exists():
        environ["PICO2D_DATA_PATH"] = str(_pico_data_dir)

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
    SDLK_SPACE,
    SDLK_UP,
    SDLK_a,
    SDLK_d,
    SDLK_r,
    SDLK_s,
    SDLK_w,
    SDL_BUTTON_LEFT,
    SDL_MOUSEBUTTONDOWN,
    SDL_MOUSEBUTTONUP,
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

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from clock_tower import ClockTowerRun, draw_clock_tower
from mirror_room import MirrorHallRun, draw_mirror_hall


SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
MENU_BUTTON_CENTER_X = 610
MENU_BUTTON_HALF_WIDTH = 290
MENU_BUTTON_HALF_HEIGHT = 34
MENU_ITEMS = (("게임 시작", 500), ("종료", 380), ("설정", 260))
SETTINGS_ITEM_Y = (555, 455, 355, 255)
VOLUME_BAR_LEFT = 515
VOLUME_BAR_RIGHT = 765
VOLUME_STEP = 10
HUB_CENTER_X = SCREEN_WIDTH / 2
HUB_CENTER_Y = SCREEN_HEIGHT / 2
HUB_MAP = (
    "#########################",
    "########...###...########",
    "###...................###",
    "##.....................##",
    "##..O...............O..##",
    "##..S...............S..##",
    "##.....................##",
    "##....D...........M....##",
    "##..S...............S..##",
    "##..O...............O..##",
    "##.....................##",
    "###..O.............O..###",
    "#####...............#####",
    "#########################",
)
HUB_START_TILE = (12, 11)
HUB_CELLAR_DOOR_TILE = (6, 1)
HUB_MIRROR_DOOR_TILE = (12, 1)
HUB_CLOCK_DOOR_TILE = (18, 1)
HUB_DIARY_TILE = (6, 7)
HUB_MIRROR_PROP_TILE = (18, 7)
HUB_DOOR_RADIUS = 88
HUB_PROP_RADIUS = 82
HUB_CLOCK_RADIUS = 148
HUB_SPEED = 210
HUB_DOORS = (
    ("cellar", "Ⅰ. 지하 저장고", HUB_CELLAR_DOOR_TILE, True),
    ("mirror", "Ⅱ. 거울의 회랑", HUB_MIRROR_DOOR_TILE, True),
    ("clock", "Ⅲ. 멈춘 시계탑", HUB_CLOCK_DOOR_TILE, True),
)
HUB_LAMP_TILES = (
    (3, 2, 300),
    (8, 2, 330),
    (16, 2, 330),
    (21, 2, 300),
    (8, 5, 345),
    (16, 5, 345),
    (8, 8, 345),
    (16, 8, 345),
    (9, 11, 325),
    (15, 11, 325),
)
MEMORY_ENTRIES = (
    (
        "cellar",
        "제1장 · 지하 저장고  (도망치던 기억)",
        (
            "\"어두운 지하실에서도 나는 끝없이 뒤를 돌아보며 도망쳤다.",
            "하지만 나를 쫓던 것은 괴물이 아니라, 실수투성이였던 어제의 나 자신이었다.\"",
        ),
        "아직 봉인된 페이지...  'Ⅰ. 지하 저장고'의 5라운드를 통과하면 첫 번째 기억이 떠오른다.",
    ),
    (
        "mirror",
        "제2장 · 거울의 회랑  (마주하는 기억)",
        (
            "\"거울 너머의 나와 처음으로 같은 걸음을 내디뎠다.",
            "피해야 할 그림자가 아니라, 함께 나아가야 할 나의 조각이었다.\"",
        ),
        "거울 너머의 기억이 아직 흐릿하게 잠겨 있다...  (2번째 미니게임 · 준비 중)",
    ),
    (
        "clock",
        "제3장 · 멈춘 시계탑  (멈춰버린 시간)",
        (
            "\"멈춰 있던 시계 바늘이 다시 움직이기 시작했다.",
            "이제는 이 기억의 저택을 벗어나, 내일로 돌아갈 시간이다.\"",
        ),
        "마지막 페이지는 찢어진 채 멈춰 있다...  (3번째 미니게임 · 준비 중)",
    ),
)
PAUSE_ITEMS = (("로비로 돌아가기", 470), ("설정", 370), ("게임 종료", 270))
PAUSE_ITEM_Y = tuple(y for _, y in PAUSE_ITEMS)
STORY_TYPE_SPEED = 26.0
STORY_FADE_DURATION = 0.45
INTRO_SCENES = (
    (
        "Ⅰ. 낯선 눈뜸",
        (
            "눈을 떠보니, 이름 모를 어두운 대저택 한가운데였다.",
            "내가 누구인지, 어째서 이곳에 있는지는 아무것도 기억나지 않는다.",
        ),
    ),
    (
        "Ⅱ. 뒤따라오는 과거",
        (
            "등에 메어진 낡은 시계 가방만이 멈추지 않고 째깍거릴 뿐.",
            "이곳에서는 내가 걸어온 과거의 흔적이 그림자가 되어 끝없이 되풀이된다.",
        ),
    ),
    (
        "Ⅲ. 피해야 할 기억",
        (
            "과거의 나에게 붙잡히면, 모든 시간은 다시 처음으로 되감기고 만다.",
            "뒤돌아보지 마. 과거를 피해 열쇠를 찾아야 이 기억의 저택을 벗어날 수 있다.",
        ),
    ),
    (
        "Ⅳ. 시간의 홀",
        (
            "거대한 시계가 놓인 홀 너머로, 잃어버린 기억의 문들이 나를 기다리고 있다.",
            "숨을 고르고 발을 내딛자. 나의 과거에서 벗어나기 위한 여정이 시작된다.",
        ),
    ),
)
MAP = (
    "#########################",
    "#.......................#",
    "#.....BBBB..............#",
    "#.......................#",
    "#.........S.......KK....#",
    "#...KK.......O..........#",
    "#............O..S.......#",
    "#............O..R.......#",
    "#.......................#",
    "#.....SR..........CCCC..#",
    "#........JJ.............#",
    "#.............R.........#",
    "#.......................#",
    "#########################",
)
TILE_WIDTH = SCREEN_WIDTH / len(MAP[0])
TILE_HEIGHT = SCREEN_HEIGHT / len(MAP)
MAP_OFFSET_X = 0
MAP_OFFSET_Y = 0
START_TILE = (2, 12)
GOAL_TILE = (22, 1)
TEST_DOOR_TILE = (3, 12)
TEST_DOOR_RADIUS = 33
PROP_SPRITES = {
    "B": (21, 19), "C": (22, 19), "J": (23, 19), "K": (21, 18),
    "S": (23, 18), "R": (16, 13),  # 석상, 무너진 돌
}
SOLID_TILES = "#O" + "".join(PROP_SPRITES) + "DM"
LAMP_TILES = ((3, 11, 340), (8, 3, 340), (11, 8, 365),
              (14, 4, 340), (20, 8, 355), (21, 2, 335))
PLAYER_START = (
    (START_TILE[0] + 0.5) * TILE_WIDTH,
    (len(MAP) - START_TILE[1] - 0.5) * TILE_HEIGHT,
)
HUB_START = (
    (HUB_START_TILE[0] + 0.5) * TILE_WIDTH,
    (len(HUB_MAP) - HUB_START_TILE[1] - 0.5) * TILE_HEIGHT,
)
HUB_DOOR_TRIGGERS = {
    room_id: (
        (tile[0] + 0.5) * TILE_WIDTH,
        (len(HUB_MAP) - tile[1] - 1.15) * TILE_HEIGHT,
    )
    for room_id, _, tile, _ in HUB_DOORS
}
CHARACTER_SCALE = 1.1
PLAYER_RADIUS = 14
PLAYER_SPEED = 205
PLAYER_ACCELERATION = 780
PLAYER_STOP_ACCELERATION = 1120
START_SAFE_RADIUS = 46
GHOST_HIT_RADIUS = 27
FIRST_GHOST_DELAY = 0.45
GHOST_INTERVAL = 0.75
GHOST_BASE_SPEED = 1.35
PRESSURE_STEPS = (6.0, 12.0, 17.0)
PRESSURE_STEP = 0.25
MIRROR_START = 6.5
MIRROR_INTERVAL = 2.4
MIRROR_GRACE = 0.9
MONSTER_HIT_RADIUS = 30
MONSTER_SLOW_SPEED = 0.48
MONSTER_SLOW_DURATION = 1.45
MONSTER_CONTACT_COOLDOWN = 1.7
MONSTER_TIME_PENALTY = 2.0
KEY_SHIFT_MIN_ROUND = 3
KEY_SHIFT_INTERVAL = 9.0
# 열쇠가 저장고의 서로 다른 구역에 나타나도록 배치한다.
ROUNDS = (
    ((17, 11), 28),
    ((4, 3), 26),
    ((15, 4), 24),
    ((5, 8), 22),
    ((21, 6), 20),
)
KEY_SHIFT_TILES = tuple(tile for tile, _ in ROUNDS)
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


def is_blocked(
    x: float,
    y: float,
    radius: float = PLAYER_RADIUS,
    tile_map: tuple[str, ...] = MAP,
) -> bool:
    """Return whether the player's collision box overlaps a wall or obstacle."""
    for corner_x in (x - radius, x + radius):
        for corner_y in (y - radius, y + radius):
            column = int((corner_x - MAP_OFFSET_X) // TILE_WIDTH)
            row_from_bottom = int((corner_y - MAP_OFFSET_Y) // TILE_HEIGHT)
            row = len(tile_map) - 1 - row_from_bottom
            if not (0 <= row < len(tile_map) and 0 <= column < len(tile_map[row])):
                return True
            if tile_map[row][column] in SOLID_TILES:
                return True
    return False


def move_player(
    x: float,
    y: float,
    move_x: float,
    move_y: float,
    delta_time: float,
    tile_map: tuple[str, ...] = MAP,
    max_speed: float = PLAYER_SPEED,
) -> tuple[float, float]:
    """Move smoothly while keeping the player inside walkable map tiles."""
    if move_x == 0 and move_y == 0:
        return x, y

    direction_length = (move_x**2 + move_y**2) ** 0.5
    movement_speed = min(max_speed, direction_length)
    distance = movement_speed * delta_time
    unit_x = move_x / direction_length
    unit_y = move_y / direction_length
    remaining = distance

    while remaining > 0:
        step = min(remaining, 8.0)
        next_x = x + unit_x * step
        next_y = y + unit_y * step

        moved_x = not is_blocked(next_x, y, tile_map=tile_map)
        moved_y = not is_blocked(x, next_y, tile_map=tile_map)
        if moved_x:
            x = next_x
        if moved_y:
            y = next_y
        if not moved_x and not moved_y:
            break
        remaining -= step
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
    stone = tile in "SR"
    base = (46, 46, 53) if stone else (38, 34, 38)
    trim = (120, 118, 124) if stone else (122, 99, 70)
    fill(x - 31, y - 29, 62, 56, base)
    fill(x - 29, y - 26, 58, 4, trim)
    size = 60 if stone else 56
    props.clip_draw(source_x * 16, props.h - (source_y + 1) * 16, 16, 16, x, y + 2, size, size)


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

    def draw_lamp_light(
        self,
        lamp: Lamp,
        rgb: tuple[int, int, int] = (153, 126, 87),
    ) -> None:
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
        points = [(lamp.x, lamp.y, (*rgb, 255))]
        ring_count = 5
        for angle in sorted(angles):
            dx, dy = cos(angle), sin(angle)
            wall_distance = ray_distance(lamp.x, lamp.y, dx, dy, lamp.reach, nearby)
            # 부딪힌 면에도 빛이 조금 닿도록 돌 표면 안쪽까지 짧게 확장한다.
            limit = min(lamp.reach, wall_distance + 9)
            for ring in range(1, ring_count + 1):
                distance = limit * ring / ring_count
                strength = (1 - distance / lamp.reach) ** 1.6
                color = (*[int(channel * strength) for channel in rgb], 255)
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


def draw_hub_tile(column: int, row: int, tile: str) -> None:
    x, y = tile_origin(column, row)
    variant = (column * 17 + row * 29) % 7
    fill(x, y, TILE_WIDTH, TILE_HEIGHT, (24, 27, 36))

    if tile == "#":
        fill(x, y + 8, TILE_WIDTH, TILE_HEIGHT - 8, (54, 58, 70))
        fill(x + 2, y + 2, 60, 9, (36, 39, 49))
        for course in range(3):
            base = y + 11 + 16 * course
            edges = (2, 26, 62) if (row + course) % 2 else (2, 38, 62)
            for left, right in zip(edges, edges[1:]):
                value = 72 + (variant + left + course * 3) % 11
                fill(x + left, base, right - left - 2, 13, (value - 2, value, value + 9))
                fill(x + left, base + 11, right - left - 2, 2,
                     (value + 14, value + 15, value + 22))
        fill(x, y + 59, 64, 5, (108, 108, 118))
        return

    if tile == "O":
        # 대저택 홀의 석재 기둥과 황동 띠 장식
        fill(x + 3, y + 3, TILE_WIDTH - 6, TILE_HEIGHT - 6, (34, 37, 47))
        fill(x + 6, y + 8, TILE_WIDTH - 12, TILE_HEIGHT - 14, (78, 81, 93))
        fill(x + 10, y + 12, TILE_WIDTH - 20, TILE_HEIGHT - 22, (98, 100, 112))
        fill(x + 12, y + 14, 6, TILE_HEIGHT - 26, (128, 128, 138))
        fill(x + 6, y + 8, TILE_WIDTH - 12, 4, (166, 132, 82))
        fill(x + 6, y + TILE_HEIGHT - 10, TILE_WIDTH - 12, 4, (166, 132, 82))
        draw_rectangle(x + 6, y + 8, x + TILE_WIDTH - 7, y + TILE_HEIGHT - 7, 132, 112, 82)
        return

    # 고급 석재 격자 바닥 타일
    checker = (column + row) % 2
    base_val = 58 if checker == 0 else 51
    tint = variant % 4
    color = (base_val + tint, base_val + 2 + tint, base_val + 11 + tint)
    fill(x + 1, y + 1, TILE_WIDTH - 2, TILE_HEIGHT - 2, color)
    fill(x + 2, y + TILE_HEIGHT - 3, TILE_WIDTH - 4, 2,
         (color[0] + 12, color[1] + 12, color[2] + 14))
    fill(x + 2, y + 1, TILE_WIDTH - 4, 2,
         (color[0] - 11, color[1] - 11, color[2] - 10))
    draw_rectangle(x + 6, y + 6, x + TILE_WIDTH - 7, y + TILE_HEIGHT - 7,
                   color[0] - 5, color[1] - 4, color[2] - 2)


def draw_hub_door_frame(column: int, accent: tuple[int, int, int]) -> tuple[float, float]:
    door_x, door_y = tile_center(column, 1)
    for pillar_col in (column - 1, column + 1):
        px, py = tile_origin(pillar_col, 1)
        fill(px + 6, py + 4, 52, TILE_HEIGHT - 4, (64, 64, 74))
        fill(px + 10, py + 8, 44, TILE_HEIGHT - 12, (94, 92, 102))
        fill(px + 8, py + 6, 48, 5, accent)
        fill(px + 8, py + TILE_HEIGHT - 8, 48, 5, accent)
        draw_circle(px + 32, py + 32, 6, *accent)
    # 문 앞 석재 디딤판
    fill(door_x - 54, door_y - 44, 108, 16, (86, 84, 94))
    fill(door_x - 50, door_y - 42, 100, 4, accent)
    return door_x, door_y


def draw_hub_details() -> None:
    cx, cy = HUB_CENTER_X, HUB_CENTER_Y

    # 좌우 회랑 바닥의 얇은 황동 장식선
    for side_col in (3, 21):
        sx, sy = tile_origin(side_col, 11)
        line_x = sx + (54 if side_col == 3 else 8)
        fill(line_x, sy + 12, 2, TILE_HEIGHT * 9 - 24, (118, 102, 78))
        for mark in range(9):
            fill(line_x - 2, sy + 32 + mark * TILE_HEIGHT, 6, 6, (158, 128, 84))

    # 세 갈래 붉은 융단: 중앙에서 세 문(좌·중·우)으로 뻗어 나간다.
    door1_x = tile_center(*HUB_CELLAR_DOOR_TILE)[0]
    door3_x = tile_center(*HUB_CLOCK_DOOR_TILE)[0]
    gallery_y = tile_center(12, 3)[1]
    carpet_bottom = tile_origin(12, 12)[1] + 16
    carpet_top = tile_origin(12, 2)[1] + TILE_HEIGHT - 4

    # 1) 상단 가로 회랑 융단 (3개의 문을 연결)
    fill(door1_x - 48, gallery_y - 38, (door3_x - door1_x) + 96, 76, (58, 28, 36))
    fill(door1_x - 42, gallery_y - 31, (door3_x - door1_x) + 84, 62, (98, 38, 48))
    fill(door1_x - 38, gallery_y - 27, (door3_x - door1_x) + 76, 2, (176, 136, 78))
    fill(door1_x - 38, gallery_y + 25, (door3_x - door1_x) + 76, 2, (176, 136, 78))

    # 2) 왼쪽·오른쪽 문으로 올라가는 세로 지선 융단
    branch_bottom = gallery_y - 28
    branch_height = carpet_top - branch_bottom
    for bx in (door1_x, door3_x):
        fill(bx - 48, branch_bottom, 96, branch_height, (58, 28, 36))
        fill(bx - 40, branch_bottom + 4, 80, branch_height - 8, (98, 38, 48))
        fill(bx - 36, branch_bottom + 6, 2, branch_height - 12, (176, 136, 78))
        fill(bx + 34, branch_bottom + 6, 2, branch_height - 12, (176, 136, 78))

    # 3) 중앙 메인 세로 융단 (출발 지점 → 중앙 시계 → 중앙 문)
    carpet_left = cx - 58
    carpet_height = carpet_top - carpet_bottom
    fill(carpet_left, carpet_bottom, 116, carpet_height, (58, 28, 36))
    fill(carpet_left + 8, carpet_bottom + 6, 100, carpet_height - 12, (98, 38, 48))
    for trim_x in (carpet_left + 12, carpet_left + 102):
        fill(trim_x, carpet_bottom + 8, 2, carpet_height - 16, (176, 136, 78))
    for index in range(11):
        dy = carpet_bottom + 36 + index * TILE_HEIGHT
        if abs(dy - cy) < 135:
            continue
        draw_line(cx - 16, dy, cx, dy + 14, 162, 116, 72)
        draw_line(cx, dy + 14, cx + 16, dy, 162, 116, 72)
        draw_line(cx + 16, dy, cx, dy - 14, 162, 116, 72)
        draw_line(cx, dy - 14, cx - 16, dy, 162, 116, 72)

    # 로비 정중앙의 거대한 기억 시계 (시간의 홀 상징 + 기억 보석 3슬롯)
    draw_circle(cx, cy, 134, 34, 36, 46, filled=True)
    draw_circle(cx, cy, 130, 148, 120, 78)
    draw_circle(cx, cy, 122, 46, 49, 62, filled=True)
    draw_circle(cx, cy, 116, 182, 146, 92)
    draw_circle(cx, cy, 104, 26, 34, 48, filled=True)
    draw_circle(cx, cy, 103, 92, 134, 142)
    draw_circle(cx, cy, 66, 62, 82, 94)
    draw_circle(cx, cy, 34, 42, 54, 68, filled=True)
    draw_circle(cx, cy, 34, 148, 122, 82)
    for hour in range(12):
        angle = pi / 2 - hour * (pi / 6)
        major = hour % 3 == 0
        inner_r = 79 if major else 88
        outer_r = 100
        color = (212, 174, 110) if major else (138, 124, 96)
        draw_line(
            cx + cos(angle) * inner_r, cy + sin(angle) * inner_r,
            cx + cos(angle) * outer_r, cy + sin(angle) * outer_r,
            *color,
        )
        if major:
            px, py = -sin(angle) * 1.5, cos(angle) * 1.5
            draw_line(
                cx + cos(angle) * inner_r + px, cy + sin(angle) * inner_r + py,
                cx + cos(angle) * outer_r + px, cy + sin(angle) * outer_r + py,
                *color,
            )

    # 1번 문 (좌측): 'Ⅰ. 지하 저장고' — 돌계단과 반쯤 열린 철문
    d1x, d1y = draw_hub_door_frame(HUB_CELLAR_DOOR_TILE[0], (176, 142, 88))
    fill(d1x - 34, d1y - 30, 68, 64, (24, 28, 36))
    for step in range(5):
        sy = d1y - 26 + step * 11
        shade = 74 - step * 9
        fill(d1x - 28, sy, 56, 9, (shade, shade + 2, shade + 10))
        fill(d1x - 28, sy, 56, 2, (34, 38, 48))
    fill(d1x - 42, d1y + 26, 84, 10, (132, 122, 114))
    fill(d1x - 42, d1y + 24, 84, 3, (192, 158, 102))
    for bar_x in (-30, -22, 20, 28):
        fill(d1x + bar_x, d1y - 28, 3, 54, (112, 118, 128))
    draw_rectangle(d1x - 34, d1y - 30, d1x + 34, d1y + 26, 174, 144, 96)

    # 2번 문 (중앙): 'Ⅱ. 거울의 회랑' — 빛나는 은빛 거울 문 (개방됨)
    d2x, d2y = draw_hub_door_frame(HUB_MIRROR_DOOR_TILE[0], (168, 142, 206))
    fill(d2x - 34, d2y - 30, 68, 64, (32, 30, 52))
    fill(d2x - 26, d2y - 24, 52, 50, (78, 70, 118))
    fill(d2x - 22, d2y - 20, 44, 42, (118, 110, 166))
    draw_line(d2x - 16, d2y - 12, d2x + 12, d2y + 16, 204, 198, 242)
    draw_line(d2x - 6, d2y - 16, d2x + 16, d2y + 6, 178, 170, 224)
    fill(d2x - 42, d2y + 26, 84, 10, (132, 124, 152))
    fill(d2x - 42, d2y + 24, 84, 3, (198, 172, 232))
    draw_rectangle(d2x - 34, d2y - 30, d2x + 34, d2y + 26, 186, 164, 220)

    # 3번 문 (우측): 'Ⅲ. 멈춘 시계탑' — 빛나는 황동 톱니 문 (개방됨)
    d3x, d3y = draw_hub_door_frame(HUB_CLOCK_DOOR_TILE[0], (192, 158, 96))
    fill(d3x - 34, d3y - 30, 68, 64, (36, 32, 28))
    fill(d3x - 26, d3y - 24, 52, 50, (68, 56, 42))
    draw_circle(d3x, d3y, 17, 212, 174, 102)
    draw_circle(d3x, d3y, 9, 166, 132, 74)
    for spoke in range(8):
        ang = spoke * pi / 4
        draw_line(
            d3x + cos(ang) * 9, d3y + sin(ang) * 9,
            d3x + cos(ang) * 21, d3y + sin(ang) * 21,
            218, 180, 106,
        )
    fill(d3x - 42, d3y + 26, 84, 10, (144, 126, 98))
    fill(d3x - 42, d3y + 24, 84, 3, (226, 190, 118))
    draw_rectangle(d3x - 34, d3y - 30, d3x + 34, d3y + 26, 204, 170, 104)

    # 왼쪽 회랑 오브젝트: '기억의 일기장' 나무 독서대와 펼쳐진 책
    dx, dy = tile_center(*HUB_DIARY_TILE)
    fill(dx - 28, dy - 24, 56, 48, (46, 36, 32))
    fill(dx - 24, dy - 20, 48, 40, (92, 62, 42))
    draw_rectangle(dx - 24, dy - 20, dx + 24, dy + 20, 158, 122, 74)
    # 펼쳐진 양피지 일기장
    fill(dx - 17, dy - 10, 16, 22, (226, 212, 182))
    fill(dx + 1, dy - 10, 16, 22, (216, 200, 168))
    fill(dx - 1, dy - 11, 2, 24, (118, 86, 56))
    for line_y in (-5, 0, 5):
        fill(dx - 14, dy + line_y, 10, 2, (124, 104, 82))
        fill(dx + 4, dy + line_y, 10, 2, (124, 104, 82))
    # 붉은 책갈피와 작은 촛불
    fill(dx + 6, dy - 15, 3, 7, (176, 56, 62))
    fill(dx - 21, dy + 10, 6, 8, (232, 224, 206))

    # 오른쪽 회랑 오브젝트: '낡은 거울' 석재 받침과 황동 전신 거울
    mx, my = tile_center(*HUB_MIRROR_PROP_TILE)
    fill(mx - 26, my - 24, 52, 48, (44, 44, 54))
    fill(mx - 22, my - 20, 44, 42, (132, 112, 82))
    fill(mx - 17, my - 15, 34, 32, (88, 108, 134))
    fill(mx - 14, my - 12, 28, 26, (118, 144, 170))
    draw_line(mx - 10, my - 8, mx + 10, my + 10, 206, 224, 238)
    draw_line(mx - 2, my - 10, mx + 11, my + 2, 178, 202, 222)
    draw_rectangle(mx - 22, my - 20, mx + 22, my + 22, 186, 154, 96)

    # 하단 출발 지점 석재 문양
    sx, sy = HUB_START
    draw_circle(sx, sy, 34, 44, 48, 60, filled=True)
    draw_circle(sx, sy, 33, 154, 128, 86)
    draw_circle(sx, sy, 26, 96, 116, 126)


class HubHall(Cellar):
    def __init__(self, props: Image) -> None:
        self.props = props
        self.lamps = [Lamp(*tile_center(column, row), reach) for column, row, reach in HUB_LAMP_TILES]
        d1x, d1y = tile_center(*HUB_CELLAR_DOOR_TILE)
        d2x, d2y = tile_center(*HUB_MIRROR_DOOR_TILE)
        d3x, d3y = tile_center(*HUB_CLOCK_DOOR_TILE)
        self.door_lights = (
            (Lamp(d1x, d1y - 36, 265), (92, 172, 184)),
            (Lamp(d2x, d2y - 36, 230), (118, 92, 158)),
            (Lamp(d3x, d3y - 36, 230), (146, 118, 72)),
        )
        self.clock_lamp = Lamp(HUB_CENTER_X, HUB_CENTER_Y, 230)
        self.walls = []
        shadow_tiles = "#O" + "".join(PROP_SPRITES)
        for row, tiles in enumerate(HUB_MAP):
            for column, tile in enumerate(tiles):
                if tile in shadow_tiles:
                    x, y = tile_origin(column, row)
                    self.walls.append((x, y, x + TILE_WIDTH, y + TILE_HEIGHT))
        self.floor = self.build_texture(self.draw_floor, pico2d.SDL_BLENDMODE_NONE)
        self.lighting = self.build_texture(self.draw_lighting, pico2d.SDL_BLENDMODE_MOD)

    def draw_floor(self) -> None:
        clear_canvas()
        for row, tiles in enumerate(HUB_MAP):
            for column, tile in enumerate(tiles):
                draw_hub_tile(column, row, tile)
        draw_hub_details()
        for row, tiles in enumerate(HUB_MAP):
            for column, tile in enumerate(tiles):
                if tile in PROP_SPRITES:
                    draw_prop(self.props, column, row, tile)
        for lamp in self.lamps:
            draw_lantern(lamp.x, lamp.y)

    def draw_lighting(self) -> None:
        p, renderer = pico2d, pico2d_core.renderer
        p.SDL_SetRenderDrawColor(renderer, 118, 128, 158, 255)
        p.SDL_RenderClear(renderer)
        p.SDL_SetRenderDrawBlendMode(renderer, p.SDL_BLENDMODE_ADD)
        for lamp in self.lamps:
            self.draw_lamp_light(lamp, (154, 124, 84))
        for lamp, rgb in self.door_lights:
            self.draw_lamp_light(lamp, rgb)
        self.draw_lamp_light(self.clock_lamp, (82, 96, 114))


def draw_player(sprite: Image, x: float, y: float, facing: str, frame: int) -> None:
    sprite.clip_draw(
        frame * SPRITE_FRAME_SIZE, SPRITE_ROWS[facing],
        SPRITE_FRAME_SIZE, SPRITE_FRAME_SIZE, x, y,
        TILE_WIDTH * CHARACTER_SCALE, TILE_HEIGHT * CHARACTER_SCALE,
    )


class MovementSample(NamedTuple):
    elapsed: float
    x: float
    y: float
    facing: str
    frame: int


class Ghost(NamedTuple):
    pose: MovementSample
    mirrored: bool
    harmless: bool


class MonsterPose(NamedTuple):
    kind: str
    x: float
    y: float
    moving_left: bool
    frame: int
    lift: float


class MonsterArt(NamedTuple):
    cell_size: int
    first_frame: int
    frame_count: int
    fps: int
    draw_size: int
    lift: float = 0.0
    bob: float = 0.0
    faces_left: bool = False


MONSTER_ART = {
    "bat": MonsterArt(16, 0, 8, 14, 58, lift=11, bob=3),
    "beetle": MonsterArt(16, 0, 8, 12, 54),
    "spider": MonsterArt(16, 0, 12, 10, 57),
    "rat": MonsterArt(32, 20, 10, 12, 68, lift=20, faces_left=True),
    "skeleton": MonsterArt(32, 4, 4, 8, 53, lift=7),
    "slime": MonsterArt(16, 0, 10, 10, 59),
}


class Patrol:
    def __init__(self, kind: str, first_round: int, tiles, speed: float, phase: float) -> None:
        self.kind = kind
        self.first_round = first_round
        self.phase = phase
        points = [tile_center(*tile) for tile in tiles]
        self.legs = [
            (a, b, hypot(b[0] - a[0], b[1] - a[1]) / speed)
            for a, b in zip(points, points[1:] + points[:1])
        ]
        self.duration = sum(leg[2] for leg in self.legs)

    def pose_at(self, elapsed: float) -> MonsterPose:
        clock = elapsed + self.phase
        leg_time = clock % self.duration
        for start, end, duration in self.legs:
            if leg_time < duration:
                break
            leg_time -= duration
        progress = leg_time / duration
        progress = progress * progress * (3 - 2 * progress)
        dx, dy = end[0] - start[0], end[1] - start[1]
        art = MONSTER_ART[self.kind]
        frame = int(clock * art.fps) % art.frame_count
        lift = art.lift + art.bob * sin(clock * 10)
        return MonsterPose(self.kind, start[0] + dx * progress, start[1] + dy * progress,
                           dx < 0, frame, lift)


# 첫 라운드부터 세 구역을 빠르게 순찰하고, 라운드마다 추가 몬스터가 합류한다.
MONSTER_PATROLS = (
    Patrol("bat", 1, ((3, 3), (8, 3), (8, 6), (3, 6)), 168, 0.5),
    Patrol("beetle", 1, ((17, 7), (22, 7), (22, 8), (17, 8)), 134, 1.6),
    Patrol("spider", 1, ((11, 8), (15, 8), (15, 10), (11, 10)), 152, 2.8),
    Patrol("rat", 2, ((16, 11), (21, 11), (21, 12), (16, 12)), 142, 0.8),
    Patrol("skeleton", 3, ((11, 2), (17, 2), (17, 3), (11, 3)), 162, 1.4),
    Patrol("slime", 4, ((2, 7), (6, 7), (6, 8), (2, 8)), 146, 1.0),
)


def pressure_clock(elapsed: float) -> float:
    # 단계가 바뀌어도 이미 진행한 재생 위치는 그대로 이어진다.
    return GHOST_BASE_SPEED * elapsed + PRESSURE_STEP * sum(
        max(0.0, elapsed - step) for step in PRESSURE_STEPS
    )


def replay_at(route: list[MovementSample], elapsed: float) -> MovementSample | None:
    if not route or elapsed < 0.0:
        return None
    duration = route[-1].elapsed
    if duration <= 0.0:
        return route[0]
    time = elapsed % (2 * duration)
    returning = time > duration
    if returning:
        time = 2 * duration - time
    index = bisect_right(route, time, key=lambda sample: sample.elapsed) - 1
    if index == len(route) - 1:
        return route[-1]
    start, end = route[index], route[index + 1]
    fraction = (time - start.elapsed) / (end.elapsed - start.elapsed)
    facing = start.facing
    if returning:
        facing = {"left": "right", "right": "left", "up": "down", "down": "up"}[facing]
    return MovementSample(
        time,
        start.x + (end.x - start.x) * fraction,
        start.y + (end.y - start.y) * fraction,
        facing,
        start.frame,
    )


def reflected_route(route: list[MovementSample]) -> list[MovementSample]:
    mirror_facing = {"left": "right", "right": "left", "up": "up", "down": "down"}
    direct = [
        MovementSample(s.elapsed, SCREEN_WIDTH - s.x, s.y, mirror_facing[s.facing], s.frame)
        for s in route
    ]
    if all(not is_blocked(s.x, s.y) for s in direct) and all(
        not is_blocked((a.x + b.x) / 2, (a.y + b.y) / 2) for a, b in zip(direct, direct[1:])
    ):
        return direct

    walkable = {(col, row) for row, tiles in enumerate(MAP)
                for col, tile in enumerate(tiles) if tile not in SOLID_TILES}

    def safe_tile(sample: MovementSample) -> tuple[int, int]:
        col = int(sample.x // TILE_WIDTH)
        row = len(MAP) - 1 - int(sample.y // TILE_HEIGHT)
        if (col, row) in walkable:
            return col, row
        return min(walkable, key=lambda tile: (
            abs(tile[0] - col) + abs(tile[1] - row), abs(tile[1] - row), tile,
        ))

    def neighbors(tile):
        x, y = tile
        return ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))

    def connect(start, goal):
        parent = {start: None}
        queue = deque([start])
        while goal not in parent:
            if not queue:
                raise ValueError("The reflected route crosses disconnected cellar tiles")
            current = queue.popleft()
            for neighbor in neighbors(current):
                if neighbor in walkable and neighbor not in parent:
                    parent[neighbor] = current
                    queue.append(neighbor)
        path = [goal]
        while path[-1] != start:
            path.append(parent[path[-1]])
        return path[::-1]

    # 좌우가 비대칭인 곳은 반전 좌표에 가장 가까운 바닥을 잇는다.
    last_tile = safe_tile(direct[0])
    result = [MovementSample(0.0, *tile_center(*last_tile), direct[0].facing, 0)]

    def add_leg(tile, segment_time: float) -> None:
        previous = result[-1]
        x, y = tile_center(*tile)
        dx, dy = x - previous.x, y - previous.y
        facing = ("right" if dx > 0 else "left") if dx else ("up" if dy > 0 else "down")
        result[-1] = previous._replace(facing=facing, frame=1)
        elapsed = previous.elapsed + max(segment_time, hypot(dx, dy) / PLAYER_SPEED)
        result.append(MovementSample(elapsed, x, y, facing, 0))

    last_change = 0.0
    for sample in direct[1:]:
        tile = safe_tile(sample)
        if tile == last_tile:
            continue
        path = connect(last_tile, tile)
        segment_time = (sample.elapsed - last_change) / (len(path) - 1)
        for next_tile in path[1:]:
            add_leg(next_tile, segment_time)
        last_tile, last_change = tile, sample.elapsed
    if len(result) == 1:
        # 짧은 경로가 반전 후 한 칸에 겹쳐도 인접한 바닥까지 왕복한다.
        next_tile = next(tile for tile in neighbors(last_tile) if tile in walkable)
        add_leg(next_tile, 0.0)
    return result


class CellarRun:
    def __init__(self) -> None:
        self.routes: list[list[MovementSample]] = []
        self.mirror_routes: list[list[MovementSample]] = []
        self.events: list[tuple[str, float, float]] = []
        self.reset()

    @property
    def round_number(self) -> int:
        return min(len(self.routes) + 1, len(ROUNDS))

    def reset(self, notice: str = "") -> None:
        self.routes.clear()
        self.mirror_routes.clear()
        self.begin_round(notice)

    def begin_round(self, notice: str = "") -> None:
        self.key_tile, self.time_limit = ROUNDS[self.round_number - 1]
        self.x, self.y = PLAYER_START
        self.facing, self.frame = "down", 0
        self.velocity_x = self.velocity_y = 0.0
        self.elapsed = self.animation_time = 0.0
        self.has_key = False
        self.recording = [self.sample(0.0)]
        self.ghosts: list[Ghost] = []
        self.patrols = [patrol for patrol in MONSTER_PATROLS if patrol.first_round <= self.round_number]
        self.monsters = [patrol.pose_at(0.0) for patrol in self.patrols]
        self.slow_until = self.monster_contact_ready = 0.0
        self.next_key_shift = KEY_SHIFT_INTERVAL
        self.notice, self.notice_until = notice, 3.0

    def sample(self, movement_elapsed: float) -> MovementSample:
        return MovementSample(movement_elapsed, self.x, self.y, self.facing, self.frame)

    def near_test_door(self) -> bool:
        x, y = tile_center(*TEST_DOOR_TILE)
        return hypot(self.x - x, self.y - y) <= TEST_DOOR_RADIUS

    def complete_round(self) -> str:
        if len(self.recording) < 2:
            return "playing"
        door_x, door_y = tile_center(*GOAL_TILE)
        self.routes.append(self.recording)
        if len(self.routes) == len(ROUNDS):
            self.events.append(("clear", door_x, door_y))
            return "clear"
        self.mirror_routes.append(reflected_route(self.recording))
        self.events.append(("next", door_x, door_y))
        self.begin_round("분신이 경로를 반복합니다. 오래 머물수록 더 빨라집니다.")
        return "next"

    def update_ghosts(self) -> None:
        self.ghosts.clear()
        clock = pressure_clock(self.elapsed)
        for routes, mirrored, start, interval in (
            (self.routes, False, FIRST_GHOST_DELAY, GHOST_INTERVAL),
            (self.mirror_routes, True, MIRROR_START, MIRROR_INTERVAL),
        ):
            for index, route in enumerate(routes):
                spawn = start + index * interval
                if self.elapsed < spawn:
                    break
                pose = replay_at(route, clock - pressure_clock(spawn))
                if pose is not None:
                    harmless = mirrored and self.elapsed < spawn + MIRROR_GRACE
                    self.ghosts.append(Ghost(pose, mirrored, harmless))

    def update(self, move_x: int, move_y: int, delta_time: float) -> str:
        self.events.clear()
        if delta_time <= 0.0:
            return "playing"
        # 이동 속도에만 감속을 적용한다. 제한 시간과 분신은 계속 진행한다.
        slowed_time = min(delta_time, max(0.0, self.slow_until - self.elapsed))
        move_time = delta_time - slowed_time * (1 - MONSTER_SLOW_SPEED)
        self.elapsed += delta_time

        input_length = hypot(move_x, move_y)
        if input_length:
            target_x = move_x / input_length * PLAYER_SPEED
            target_y = move_y / input_length * PLAYER_SPEED
        else:
            target_x = target_y = 0.0

        def approach(current: float, target: float, acceleration: float) -> float:
            if current < target:
                return min(target, current + acceleration * move_time)
            return max(target, current - acceleration * move_time)

        acceleration = PLAYER_ACCELERATION if input_length else PLAYER_STOP_ACCELERATION
        self.velocity_x = approach(self.velocity_x, target_x, acceleration)
        self.velocity_y = approach(self.velocity_y, target_y, acceleration)

        previous = self.x, self.y
        self.x, self.y = move_player(
            self.x, self.y, self.velocity_x, self.velocity_y, move_time
        )
        self.frame = 0
        if (self.x, self.y) != previous:
            if abs(move_x) > abs(move_y):
                self.facing = "right" if move_x > 0 else "left"
            else:
                self.facing = "up" if move_y > 0 else "down"
            self.animation_time += move_time
            self.frame = int(self.animation_time * 8) % 4
            # 라운드 시계와 별도로, 좌표가 바뀐 프레임의 시간만 재생 기록에 더한다.
            movement_elapsed = self.recording[-1].elapsed + delta_time
            self.recording.append(self.sample(movement_elapsed))
        self.update_ghosts()
        self.monsters = [patrol.pose_at(self.elapsed) for patrol in self.patrols]
        if self.elapsed >= self.monster_contact_ready and any(
            hypot(self.x - monster.x, self.y - monster.y) <= MONSTER_HIT_RADIUS
            for monster in self.monsters
        ):
            self.slow_until = self.elapsed + MONSTER_SLOW_DURATION
            self.monster_contact_ready = self.elapsed + MONSTER_CONTACT_COOLDOWN
            self.time_limit = max(self.elapsed + 0.2, self.time_limit - MONSTER_TIME_PENALTY)
            self.notice = "몬스터와 부딪혀 느려지고 제한 시간이 2초 줄었습니다!"
            self.notice_until = self.elapsed + 2.0
            self.events.append(("monster", self.x, self.y))
        # 3라운드부터는 일정 시간 동안 열쇠를 못 얻으면 열쇠가 다른 구역으로 이동한다.
        if (
            not self.has_key
            and self.round_number >= KEY_SHIFT_MIN_ROUND
            and self.elapsed >= self.next_key_shift
        ):
            self.next_key_shift += KEY_SHIFT_INTERVAL
            candidates = [tile for tile in KEY_SHIFT_TILES if tile != self.key_tile]
            self.key_tile = random.choice(candidates)
            new_kx, new_ky = tile_center(*self.key_tile)
            self.notice = "열쇠가 다른 구역으로 이동했습니다!"
            self.notice_until = self.elapsed + 2.2
            self.events.append(("key_shift", new_kx, new_ky))
        # 같은 위치에서 출발한 기록이 겹쳐도 계단 앞에서는 안전하다.
        if hypot(self.x - PLAYER_START[0], self.y - PLAYER_START[1]) > START_SAFE_RADIUS:
            for ghost in self.ghosts:
                if not ghost.harmless and hypot(self.x - ghost.pose.x, self.y - ghost.pose.y) < GHOST_HIT_RADIUS:
                    hit_x, hit_y = self.x, self.y
                    self.reset("분신과 접촉했습니다. 1라운드부터 다시 시작합니다.")
                    self.events.append(("ghost", hit_x, hit_y))
                    return "reset"
        if self.elapsed >= self.time_limit:
            hit_x, hit_y = self.x, self.y
            self.reset("시간이 끝났습니다. 1라운드부터 다시 시작합니다.")
            self.events.append(("timeout", hit_x, hit_y))
            return "reset"
        key_x, key_y = tile_center(*self.key_tile)
        if not self.has_key and hypot(self.x - key_x, self.y - key_y) < 24:
            self.has_key = True
            self.notice = "열쇠를 찾았습니다. 북동쪽 철문으로 가세요."
            self.notice_until = self.elapsed + 2.5
            self.events.append(("key", key_x, key_y))
        door_x, door_y = tile_center(*GOAL_TILE)
        if self.has_key and hypot(self.x - door_x, self.y - door_y) < 25:
            return self.complete_round()
        return "playing"


class SoundBank:
    """Manage gothic BGM loops and SFX chunks safely with independent volume sliders."""

    def __init__(self, sounds_dir: Path) -> None:
        self.bgm_volume = 70
        self.sfx_volume = 80
        self.saved_bgm_volume = 70
        self.saved_sfx_volume = 80
        self.paused_duck = False
        self.current_bgm: str | None = None
        self.bgms: dict[str, object] = {}
        self.sfx: dict[str, object] = {}
        if not pico2d_core.audio_on or not sounds_dir.exists():
            return
        for name in ("hub", "cellar"):
            path = sounds_dir / f"bgm_{name}.wav"
            if path.exists():
                self.bgms[name] = pico2d.load_music(str(path))
        for name in (
            "ui_move", "ui_confirm", "story_tick", "step",
            "key", "round_clear", "stage_clear", "monster_hit", "ghost_hit",
        ):
            path = sounds_dir / f"sfx_{name}.wav"
            if path.exists():
                self.sfx[name] = pico2d.load_wav(str(path))
        self.apply_volumes()

    def apply_volumes(self) -> None:
        if not pico2d_core.audio_on:
            return
        raw_bgm = int(128 * self.bgm_volume / 100)
        if self.paused_duck:
            raw_bgm //= 3
        raw_sfx = int(128 * self.sfx_volume / 100)
        Mix_VolumeMusic(raw_bgm)
        Mix_Volume(-1, raw_sfx)

    def set_bgm_volume(self, value: int) -> None:
        self.bgm_volume = max(0, min(100, int(value)))
        if self.bgm_volume > 0:
            self.saved_bgm_volume = self.bgm_volume
        self.apply_volumes()

    def set_sfx_volume(self, value: int) -> None:
        self.sfx_volume = max(0, min(100, int(value)))
        if self.sfx_volume > 0:
            self.saved_sfx_volume = self.sfx_volume
        self.apply_volumes()

    def toggle_bgm_mute(self) -> None:
        if self.bgm_volume > 0:
            self.saved_bgm_volume = self.bgm_volume
            self.bgm_volume = 0
        else:
            self.bgm_volume = self.saved_bgm_volume or 70
        self.apply_volumes()

    def toggle_sfx_mute(self) -> None:
        if self.sfx_volume > 0:
            self.saved_sfx_volume = self.sfx_volume
            self.sfx_volume = 0
        else:
            self.sfx_volume = self.saved_sfx_volume or 80
        self.apply_volumes()

    def set_paused_duck(self, paused: bool) -> None:
        self.paused_duck = paused
        self.apply_volumes()

    def play_bgm(self, name: str) -> None:
        if name == self.current_bgm:
            return
        bgm = self.bgms.get(name)
        if bgm is None:
            return
        self.current_bgm = name
        bgm.repeat_play()
        self.apply_volumes()

    def play(self, name: str) -> None:
        if self.sfx_volume <= 0:
            return
        chunk = self.sfx.get(name)
        if chunk is not None:
            chunk.play()

    def close(self) -> None:
        if pico2d_core.audio_on:
            pico2d.Mix_HaltMusic()
        self.bgms.clear()
        self.sfx.clear()


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "age", "life", "size", "color")

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: float,
        size: float,
        color: tuple[int, int, int],
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.age = 0.0
        self.life = life
        self.size = size
        self.color = color


class ShockRing:
    __slots__ = ("x", "y", "start_r", "end_r", "age", "life", "color")

    def __init__(
        self,
        x: float,
        y: float,
        start_r: float,
        end_r: float,
        life: float,
        color: tuple[int, int, int],
    ) -> None:
        self.x = x
        self.y = y
        self.start_r = start_r
        self.end_r = end_r
        self.age = 0.0
        self.life = life
        self.color = color


class EffectsManager:
    """Lightweight particles, shockwaves, screen flash, and damped camera shake."""

    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.rings: list[ShockRing] = []
        self.flash_color: tuple[int, int, int] = (255, 255, 255)
        self.flash_alpha: int = 0
        self.flash_age: float = 0.0
        self.flash_life: float = 0.0
        self.shake_age: float = 0.0
        self.shake_duration: float = 0.0
        self.shake_magnitude: float = 0.0

    def clear(self) -> None:
        self.particles.clear()
        self.rings.clear()
        self.flash_life = 0.0
        self.shake_duration = 0.0

    def trigger_flash(self, color: tuple[int, int, int], alpha: int, life: float) -> None:
        self.flash_color = color
        self.flash_alpha = alpha
        self.flash_age = 0.0
        self.flash_life = life

    def trigger_shake(self, magnitude: float, duration: float) -> None:
        self.shake_magnitude = max(self.shake_magnitude, magnitude)
        self.shake_duration = max(self.shake_duration - self.shake_age, duration)
        self.shake_age = 0.0

    def spawn_dust(self, x: float, y: float, color: tuple[int, int, int] = (176, 168, 154)) -> None:
        if len(self.particles) > 140:
            return
        self.particles.append(
            Particle(
                x + random.uniform(-6, 6),
                y - 12 + random.uniform(-3, 3),
                random.uniform(-16, 16),
                random.uniform(6, 22),
                random.uniform(0.28, 0.48),
                random.uniform(3.0, 5.0),
                color,
            )
        )

    def burst_key(self, x: float, y: float) -> None:
        for index in range(22):
            angle = index * (2 * pi / 22) + random.uniform(-0.15, 0.15)
            speed = random.uniform(70, 210)
            color = (255, 224, 118) if index % 2 == 0 else (255, 186, 78)
            self.particles.append(
                Particle(x, y, cos(angle) * speed, sin(angle) * speed,
                         random.uniform(0.35, 0.65), random.uniform(4.0, 7.0), color)
            )
        self.rings.append(ShockRing(x, y, 12, 86, 0.42, (255, 220, 112)))
        self.rings.append(ShockRing(x, y, 8, 52, 0.28, (255, 245, 190)))
        self.trigger_flash((255, 214, 110), 48, 0.22)
        self.trigger_shake(4.5, 0.16)

    def burst_round_clear(self, x: float, y: float) -> None:
        for index in range(26):
            angle = index * (2 * pi / 26) + random.uniform(-0.12, 0.12)
            speed = random.uniform(80, 240)
            color = (122, 232, 206) if index % 2 == 0 else (246, 216, 146)
            self.particles.append(
                Particle(x, y, cos(angle) * speed, sin(angle) * speed,
                         random.uniform(0.42, 0.78), random.uniform(4.0, 7.5), color)
            )
        self.rings.append(ShockRing(x, y, 14, 125, 0.52, (124, 232, 208)))
        self.trigger_flash((142, 228, 212), 62, 0.34)
        self.trigger_shake(5.5, 0.20)

    def burst_monster_hit(self, x: float, y: float) -> None:
        for index in range(16):
            angle = index * (2 * pi / 16) + random.uniform(-0.2, 0.2)
            speed = random.uniform(60, 175)
            color = (248, 152, 76) if index % 2 == 0 else (228, 98, 72)
            self.particles.append(
                Particle(x, y, cos(angle) * speed, sin(angle) * speed,
                         random.uniform(0.28, 0.52), random.uniform(4.0, 6.5), color)
            )
        self.rings.append(ShockRing(x, y, 14, 72, 0.32, (246, 154, 82)))
        self.trigger_flash((238, 124, 68), 64, 0.24)
        self.trigger_shake(9.0, 0.26)

    def burst_ghost_hit(self, x: float, y: float) -> None:
        for index in range(28):
            angle = index * (2 * pi / 28) + random.uniform(-0.14, 0.14)
            speed = random.uniform(90, 270)
            color = (112, 228, 244) if index % 2 == 0 else (238, 108, 124)
            self.particles.append(
                Particle(x, y, cos(angle) * speed, sin(angle) * speed,
                         random.uniform(0.40, 0.75), random.uniform(4.5, 8.0), color)
            )
        self.rings.append(ShockRing(x, y, 16, 140, 0.48, (112, 228, 244)))
        self.rings.append(ShockRing(x, y, 10, 95, 0.36, (240, 108, 128)))
        self.trigger_flash((128, 214, 232), 110, 0.42)
        self.trigger_shake(13.0, 0.38)

    def update(self, delta_time: float) -> None:
        if delta_time <= 0.0:
            return
        drag = max(0.0, 1.0 - delta_time * 3.8)
        alive_particles: list[Particle] = []
        for particle in self.particles:
            particle.age += delta_time
            if particle.age < particle.life:
                particle.x += particle.vx * delta_time
                particle.y += particle.vy * delta_time
                particle.vx *= drag
                particle.vy *= drag
                alive_particles.append(particle)
        self.particles = alive_particles

        alive_rings: list[ShockRing] = []
        for ring in self.rings:
            ring.age += delta_time
            if ring.age < ring.life:
                alive_rings.append(ring)
        self.rings = alive_rings

        if self.flash_life > 0.0:
            self.flash_age += delta_time
            if self.flash_age >= self.flash_life:
                self.flash_life = 0.0

        if self.shake_duration > 0.0:
            self.shake_age += delta_time
            if self.shake_age >= self.shake_duration:
                self.shake_duration = 0.0
                self.shake_magnitude = 0.0

    def shake_offset(self) -> tuple[int, int]:
        if self.shake_duration <= 0.0 or self.shake_magnitude <= 0.0:
            return 0, 0
        strength = (1.0 - self.shake_age / self.shake_duration) * self.shake_magnitude
        return int(random.uniform(-strength, strength)), int(random.uniform(-strength, strength))

    def draw_world(self) -> None:
        for ring in self.rings:
            progress = ring.age / ring.life
            radius = int(ring.start_r + (ring.end_r - ring.start_r) * (1 - (1 - progress) ** 2))
            alpha = max(0, int(210 * (1.0 - progress)))
            if radius > 1 and alpha > 2:
                draw_circle(ring.x, ring.y, radius, *ring.color, alpha)
                if radius > 3:
                    draw_circle(ring.x, ring.y, radius - 2, *ring.color, alpha // 2)
        for particle in self.particles:
            progress = particle.age / particle.life
            alpha = max(0, int(235 * (1.0 - progress)))
            size = max(2.0, particle.size * (1.0 - progress * 0.45))
            fill(particle.x - size / 2, particle.y - size / 2, size, size, (*particle.color, alpha))

    def draw_overlay(self) -> None:
        if self.flash_life > 0.0:
            progress = self.flash_age / self.flash_life
            alpha = max(0, int(self.flash_alpha * (1.0 - progress) ** 1.5))
            if alpha > 2:
                fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (*self.flash_color, alpha))


def draw_ghost_trails(run: CellarRun) -> None:
    """Draw subtle floor route threads, 1.2s ahead telegraph lines, and upcoming spawn rings."""
    clock = pressure_clock(run.elapsed)
    for routes, mirrored, start, interval in (
        (run.routes, False, FIRST_GHOST_DELAY, GHOST_INTERVAL),
        (run.mirror_routes, True, MIRROR_START, MIRROR_INTERVAL),
    ):
        color = (208, 147, 255) if mirrored else (102, 220, 240)
        for index, route in enumerate(routes):
            if not route:
                continue
            spawn = start + index * interval
            time_until_spawn = spawn - run.elapsed
            # 스폰 2.5초 전부터 출발 위치에 수렴하는 예고 링을 표시한다.
            if 0.0 < time_until_spawn <= 2.5:
                progress = 1.0 - time_until_spawn / 2.5
                sx, sy = route[0].x, route[0].y
                outer_r = int(42 - 22 * progress)
                alpha = int(75 + 135 * progress)
                draw_circle(sx, sy, outer_r, *color, alpha)
                draw_circle(sx, sy, max(4, int(10 * progress)), *color, alpha // 2, filled=True)
                continue
            if time_until_spawn > 2.5:
                continue

            # 1) 바닥에 깔리는 희미한 전체 과거 경로 점선
            duration = route[-1].elapsed
            if duration > 0.2:
                step = 0.42
                sample_t = 0.0
                while sample_t <= duration:
                    pt = replay_at(route, sample_t)
                    if pt is not None:
                        fill(pt.x - 1.5, pt.y - 1.5, 3, 3, (*color, 44 if mirrored else 56))
                    sample_t += step

            # 2) 현재 분신이 앞으로 ~1.2초 동안 이동할 방향 예고선
            ghost_clock = clock - pressure_clock(spawn)
            current = replay_at(route, ghost_clock)
            if current is None:
                continue
            prev_x, prev_y = current.x, current.y
            harmless = mirrored and run.elapsed < spawn + MIRROR_GRACE
            base_alpha = 70 if harmless else 145
            steps = 7
            for step_i in range(1, steps + 1):
                ahead = replay_at(route, ghost_clock + step_i * 0.22)
                if ahead is None:
                    break
                fade = 1.0 - (step_i - 1) / steps
                alpha = max(24, int(base_alpha * fade))
                if hypot(ahead.x - prev_x, ahead.y - prev_y) < 120:
                    draw_line(prev_x, prev_y, ahead.x, ahead.y, *color, alpha)
                if step_i == steps:
                    draw_circle(ahead.x, ahead.y, 4, *color, alpha + 25, filled=True)
                prev_x, prev_y = ahead.x, ahead.y


def draw_player_status_effects(run: CellarRun) -> None:
    """Draw slow indicator, near-ghost danger warning, and unlocked exit door pulse."""
    # 슬로우 상태일 때 발밑에 주황빛 감속 링 표시
    if run.elapsed < run.slow_until:
        pulse = 0.5 + 0.5 * sin(run.elapsed * 16.0)
        draw_circle(run.x, run.y - 6, int(22 + 4 * pulse), 246, 164, 96, 175)

    # 안전 구역 밖에서 치명적인 분신이 가까이 다가오면 경고 링 표시
    if hypot(run.x - PLAYER_START[0], run.y - PLAYER_START[1]) > START_SAFE_RADIUS:
        closest = 9999.0
        for ghost in run.ghosts:
            if not ghost.harmless:
                closest = min(closest, hypot(run.x - ghost.pose.x, run.y - ghost.pose.y))
        if closest < 130.0:
            urgency = max(0.0, min(1.0, (130.0 - closest) / 95.0))
            pulse = 0.5 + 0.5 * sin(run.elapsed * 18.0)
            ring_r = int(26 + 8 * pulse)
            draw_circle(run.x, run.y, ring_r, 246, 98, 108, int(85 + 140 * urgency))
            # 화면 상하좌우 얇은 붉은 위험 테두리
            edge_alpha = int(42 * urgency * (0.6 + 0.4 * pulse))
            fill(0, 0, SCREEN_WIDTH, 10, (235, 68, 82, edge_alpha))
            fill(0, SCREEN_HEIGHT - 10, SCREEN_WIDTH, 10, (235, 68, 82, edge_alpha))
            fill(0, 0, 10, SCREEN_HEIGHT, (235, 68, 82, edge_alpha))
            fill(SCREEN_WIDTH - 10, 0, 10, SCREEN_HEIGHT, (235, 68, 82, edge_alpha))

    # 열쇠 획득 후 북동쪽 출구 철문에 생동감 있는 가이드 펄스 표시
    if run.has_key:
        door_x, door_y = tile_center(*GOAL_TILE)
        pulse = 0.5 + 0.5 * sin(run.elapsed * 5.0)
        draw_circle(door_x, door_y, int(34 + 6 * pulse), 108, 226, 178, int(52 + 38 * pulse))
        draw_circle(door_x, door_y, 24, 108, 226, 178, int(26 + 20 * pulse), filled=True)
        fill(door_x - 22, door_y - 27, 44, 4, (118, 236, 188))


def draw_ghost(sprite: Image, ghost: Ghost) -> None:
    sample = ghost.pose
    color = (208, 147, 255) if ghost.mirrored else (102, 220, 240)
    draw_circle(sample.x, sample.y, PLAYER_RADIUS + 2, *color, 90 if ghost.harmless else 180)
    pico2d.SDL_SetTextureColorMod(sprite.texture, *color)
    sprite.opacify(0.28 if ghost.harmless else 0.58)
    draw_player(sprite, sample.x, sample.y, sample.facing, sample.frame)
    sprite.opacify(1.0)
    pico2d.SDL_SetTextureColorMod(sprite.texture, 255, 255, 255)


def draw_monster(sprite: Image, monster: MonsterPose) -> None:
    art = MONSTER_ART[monster.kind]
    cell = art.cell_size
    row, col = divmod(art.first_frame + monster.frame, sprite.w // cell)
    draw_circle(monster.x, monster.y - 8, 11, 9, 10, 13, 165, filled=True)
    draw_circle(monster.x, monster.y - 1, 18, 222, 148, 79, 92)
    sprite.clip_composite_draw(
        col * cell, sprite.h - (row + 1) * cell, cell, cell, 0,
        "h" if monster.moving_left != art.faces_left else "",
        monster.x, monster.y + monster.lift, art.draw_size, art.draw_size,
    )


def draw_test_door(hint_font: Font, nearby: bool) -> None:
    x, y = tile_center(*TEST_DOOR_TILE)
    trim = (129, 224, 220) if nearby else (74, 140, 145)
    fill(x - 21, y - 23, 42, 46, (27, 39, 45))
    draw_rectangle(x - 20, y - 22, x + 20, y + 22, *trim)
    fill(x - 13, y - 16, 26, 33, (35, 73, 79))
    draw_line(x - 8, y + 9, x + 8, y + 9, *trim)
    fill(x + 6, y - 4, 4, 4, trim)
    label = "ENTER" if nearby else "TEST"
    draw_centered_text(hint_font, label, x, y + 34, trim)


def draw_run_hud(menu_font: Font, hint_font: Font, run: CellarRun) -> None:
    fill(12, 847, 1458, 44, (23, 20, 24, 236))
    draw_rectangle(12, 847, 1470, 891, 133, 106, 74, filled=False)
    menu_font.draw(27, 867, "대저택 지하 저장고", (239, 209, 158))
    remaining = max(0, int(run.time_limit - run.elapsed + 0.999))
    key = "YES" if run.has_key else "NO"
    low_time = remaining <= 10
    time_pulse = low_time and int(run.elapsed * 4) % 2 == 0
    hint_font.draw(316, 865, f"ROUND {run.round_number}/{len(ROUNDS)}", (224, 210, 187))
    hint_font.draw(
        444, 865, f"TIME {remaining:02d}s",
        (255, 114, 104) if time_pulse else ((248, 166, 112) if low_time else (224, 210, 187)),
    )
    hint_font.draw(
        564, 865, f"KEY {key}",
        (118, 234, 184) if run.has_key else (224, 210, 187),
    )
    mirrors = sum(ghost.mirrored for ghost in run.ghosts)
    originals = len(run.ghosts) - mirrors
    speed = 1.0
    if run.routes:
        speed = GHOST_BASE_SPEED + PRESSURE_STEP * sum(run.elapsed >= step for step in PRESSURE_STEPS)
    hint_font.draw(736, 865, f"SHADOWS {originals}", (139, 207, 212))
    hint_font.draw(896, 865, f"SPEED x{speed:.1f}", (239, 184, 123) if speed > 1 else (224, 210, 187))
    if mirrors < len(run.mirror_routes):
        until = max(0, int(MIRROR_START + mirrors * MIRROR_INTERVAL - run.elapsed + 0.999))
        mirror_label = f"MIRRORS {mirrors}   NEXT {until:02d}s"
    else:
        mirror_label = f"MIRRORS {mirrors}"
    hint_font.draw(1080, 865, mirror_label, (208, 147, 255))
    slowed = run.elapsed < run.slow_until
    monster_label = f"MOBS {len(run.monsters)}" + (" SLOW" if slowed else "")
    hint_font.draw(1325, 865, monster_label, (246, 164, 96) if slowed else (224, 210, 187))
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


class CrispFont:
    """Render supersampled, linearly-filtered, cached text so glyphs stay sharp at any window scale."""

    def __init__(self, path: str, size: int, scale: int = 2) -> None:
        self.scale = scale
        self.font = pico2d.TTF_OpenFont(path.encode("utf-8"), size * scale)
        if not self.font:
            raise RuntimeError(f"Could not load font '{path}': {sdl_error_message()}")
        pico2d.TTF_SetFontHinting(self.font, pico2d.TTF_HINTING_LIGHT)
        self._cache: dict[tuple[str, tuple[int, int, int]], tuple[object, float, float]] = {}

    def _entry(self, text: str, color: tuple[int, int, int]):
        key = (text, color)
        entry = self._cache.get(key)
        if entry is not None:
            return entry
        if len(self._cache) >= 256:
            self.clear_cache()
        sdl_color = pico2d.SDL_Color(color[0], color[1], color[2], 255)
        surface = pico2d.TTF_RenderUTF8_Blended(self.font, text.encode("utf-8"), sdl_color)
        if not surface:
            raise RuntimeError(f"Could not render text '{text}': {sdl_error_message()}")
        try:
            texture = pico2d.SDL_CreateTextureFromSurface(pico2d_core.renderer, surface)
            if not texture:
                raise RuntimeError(f"Could not create text texture: {sdl_error_message()}")
            pico2d.SDL_SetTextureScaleMode(texture, pico2d.SDL_ScaleModeBest)
            width = surface.contents.w / self.scale
            height = surface.contents.h / self.scale
        finally:
            pico2d.SDL_FreeSurface(surface)
        entry = (texture, width, height)
        self._cache[key] = entry
        return entry

    def measure(self, text: str) -> tuple[float, float]:
        text_width = ctypes.c_int()
        text_height = ctypes.c_int()
        result = pico2d.TTF_SizeUTF8(
            self.font,
            text.encode("utf-8"),
            ctypes.byref(text_width),
            ctypes.byref(text_height),
        )
        if result != 0:
            raise RuntimeError(f"Could not measure text: {sdl_error_message()}")
        return text_width.value / self.scale, text_height.value / self.scale

    def draw(
        self,
        x: float,
        y: float,
        text: str,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        if not text:
            return
        texture, width, height = self._entry(text, color)
        dest = pico2d.SDL_FRect(
            round(x),
            round(SCREEN_HEIGHT - y - height / 2),
            width,
            height,
        )
        pico2d.SDL_RenderCopyF(pico2d_core.renderer, texture, None, ctypes.byref(dest))

    def clear_cache(self) -> None:
        for texture, _, _ in self._cache.values():
            pico2d.SDL_DestroyTexture(texture)
        self._cache.clear()

    def close(self) -> None:
        self.clear_cache()
        if self.font:
            pico2d.TTF_CloseFont(self.font)
            self.font = None


def draw_centered_text(
    font: Font | CrispFont,
    text: str,
    center_x: float,
    y: float,
    color: tuple[int, int, int],
) -> None:
    if isinstance(font, CrispFont):
        width, _ = font.measure(text)
    else:
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
        width = text_width.value
    font.draw(center_x - width / 2, y, text, color)


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


def hub_interaction_target(player_x: float, player_y: float) -> str | None:
    """Return the closest interactive door or story object within range in the lobby."""
    for room_id, _, _, _ in HUB_DOORS:
        dx, dy = HUB_DOOR_TRIGGERS[room_id]
        if hypot(player_x - dx, player_y - dy) <= HUB_DOOR_RADIUS:
            return room_id
    diary_x, diary_y = tile_center(*HUB_DIARY_TILE)
    if hypot(player_x - diary_x, player_y - diary_y) <= HUB_PROP_RADIUS:
        return "diary"
    mirror_x, mirror_y = tile_center(*HUB_MIRROR_PROP_TILE)
    if hypot(player_x - mirror_x, player_y - mirror_y) <= HUB_PROP_RADIUS:
        return "mirror_prop"
    if hypot(player_x - HUB_CENTER_X, player_y - HUB_CENTER_Y) <= 105:
        return "clock_center"
    return None


def draw_hub_clock_hands(elapsed: float, cleared_rooms: set[str]) -> None:
    cx, cy = HUB_CENTER_X, HUB_CENTER_Y
    pulse = 0.5 + 0.5 * sin(elapsed * 2.2)
    lit_count = len(cleared_rooms)
    core_color = (242, 206, 122) if lit_count >= 3 else (96, 198, 206)
    draw_circle(cx, cy, 24 + lit_count * 4, *core_color, int(20 + lit_count * 10 + 14 * pulse), filled=True)

    # 중앙 시계 테두리의 기억 보석 슬롯 3개 (10시: 지하 저장고, 12시: 거울의 회랑, 2시: 멈춘 시계탑)
    gem_slots = (
        ("cellar", pi * 5 / 6, (108, 226, 224)),
        ("mirror", pi / 2, (206, 152, 252)),
        ("clock", pi / 6, (246, 204, 112)),
    )
    for room_id, angle, gem_color in gem_slots:
        gx = cx + cos(angle) * 119
        gy = cy + sin(angle) * 119
        unlocked = room_id in cleared_rooms
        draw_circle(gx, gy, 13, 28, 32, 42, filled=True)
        draw_circle(gx, gy, 13, 188, 154, 96)
        if unlocked:
            draw_circle(gx, gy, 18, *gem_color, int(36 + 24 * pulse), filled=True)
            draw_circle(gx, gy, 9, *gem_color, filled=True)
            draw_circle(gx, gy, 4, 255, 250, 234, filled=True)
            draw_line(gx, gy, cx, cy, *gem_color, int(42 + 26 * pulse))
        else:
            draw_circle(gx, gy, 8, 20, 24, 34, filled=True)
            draw_circle(gx, gy, 8, 76, 86, 102)

    # 시침, 분침, 초침이 천천히 돌아가며 '시간의 홀' 분위기를 살린다.
    hands = (
        (pi / 2 - elapsed * 0.04, 52, (198, 158, 96), 2),
        (pi / 2 - elapsed * 0.24, 78, (232, 200, 134), 1),
        (pi / 2 - elapsed * 1.15, 92, (118, 214, 220), 0),
    )
    for angle, length, color, thickness in hands:
        ex = cx + cos(angle) * length
        ey = cy + sin(angle) * length
        draw_line(cx, cy, ex, ey, *color)
        if thickness > 0:
            px, py = -sin(angle), cos(angle)
            for offset in range(1, thickness + 1):
                draw_line(cx + px * offset, cy + py * offset,
                          ex + px * offset, ey + py * offset, *color)
                draw_line(cx - px * offset, cy - py * offset,
                          ex - px * offset, ey - py * offset, *color)
    draw_circle(cx, cy, 7, 214, 176, 110, filled=True)
    draw_circle(cx, cy, 3, 128, 224, 230, filled=True)


def draw_hub_gate_effects(
    elapsed: float,
    target: str | None,
    cleared_rooms: set[str],
) -> None:
    pulse = 0.5 + 0.5 * sin(elapsed * 3.2)

    # 1번 문 (지하 저장고): 미클리어 시 청록빛, 클리어 후 황금빛 완료 오라
    d1x, d1y = tile_center(*HUB_CELLAR_DOOR_TILE)
    cellar_cleared = "cellar" in cleared_rooms
    near_cellar = target == "cellar"
    c1 = (246, 206, 114) if cellar_cleared else (102, 214, 218)
    c1_inner = (255, 240, 196) if cellar_cleared else (190, 242, 240)
    a1 = int((48 if near_cellar else 28) + 18 * pulse)
    draw_circle(d1x, d1y - 4, 34, *c1, a1, filled=True)
    draw_circle(d1x, d1y - 4, 18, *c1_inner, a1 + 15, filled=True)
    if near_cellar:
        fill(d1x - 50, d1y - 43, 100, 5, (*c1, 175))
    for mote in range(5):
        rise = (elapsed * (16 + mote * 3) + mote * 13) % 52
        mx = d1x + 22 * sin(elapsed * 1.8 + mote * 1.7)
        my = d1y - 26 + rise
        alpha = int((145 if near_cellar else 95) * sin(pi * rise / 52))
        fill(mx, my, 3, 3, (*c1_inner, alpha))

    # 2번 문 (거울의 회랑): 개방된 은빛·보라 포털 (클리어 시 황금빛)
    d2x, d2y = tile_center(*HUB_MIRROR_DOOR_TILE)
    mirror_cleared = "mirror" in cleared_rooms
    near_mirror = target == "mirror"
    c2 = (246, 206, 114) if mirror_cleared else (196, 154, 248)
    c2_inner = (255, 240, 196) if mirror_cleared else (232, 212, 255)
    a2 = int((46 if near_mirror else 26) + 16 * pulse)
    draw_circle(d2x, d2y - 4, 34, *c2, a2, filled=True)
    draw_circle(d2x, d2y - 4, 18, *c2_inner, a2 + 12, filled=True)
    if near_mirror:
        fill(d2x - 50, d2y - 43, 100, 5, (*c2, 175))
    for mote in range(4):
        rise = (elapsed * (15 + mote * 3) + mote * 15) % 50
        mx = d2x + 20 * sin(elapsed * 1.9 + mote * 1.5)
        my = d2y - 24 + rise
        alpha = int((135 if near_mirror else 85) * sin(pi * rise / 50))
        fill(mx, my, 3, 3, (*c2_inner, alpha))

    # 3번 문 (멈춘 시계탑): 개방된 황금 시계탑 오라
    d3x, d3y = tile_center(*HUB_CLOCK_DOOR_TILE)
    near_clock = target == "clock"
    c3 = (248, 206, 112)
    c3_inner = (255, 240, 192)
    a3 = int((46 if near_clock else 26) + 16 * pulse)
    draw_circle(d3x, d3y - 4, 34, *c3, a3, filled=True)
    draw_circle(d3x, d3y - 4, 18, *c3_inner, a3 + 12, filled=True)
    if near_clock:
        fill(d3x - 50, d3y - 43, 100, 5, (*c3, 175))
    for mote in range(4):
        rise = (elapsed * (15 + mote * 3) + mote * 14) % 50
        mx = d3x + 20 * sin(elapsed * 2.0 + mote * 1.6)
        my = d3y - 24 + rise
        alpha = int((135 if near_clock else 85) * sin(pi * rise / 50))
        fill(mx, my, 3, 3, (*c3_inner, alpha))

    # 왼쪽 회랑 일기장 옆 작은 촛불 깜박임
    diary_x, diary_y = tile_center(*HUB_DIARY_TILE)
    candle_glow = int(34 + 14 * sin(elapsed * 6.5))
    draw_circle(diary_x - 18, diary_y + 18, 12, 255, 174, 72, candle_glow, filled=True)
    draw_circle(diary_x - 18, diary_y + 18, 4, 255, 240, 174, 170 + candle_glow // 2, filled=True)
    if target == "diary":
        draw_circle(diary_x, diary_y, 38, 238, 206, 134, int(90 + 40 * pulse))

    # 오른쪽 회랑 낡은 거울 반짝임
    mirror_x, mirror_y = tile_center(*HUB_MIRROR_PROP_TILE)
    draw_circle(mirror_x, mirror_y + 2, 22, 162, 208, 234, int(18 + 14 * pulse), filled=True)
    if target == "mirror_prop":
        draw_circle(mirror_x, mirror_y, 38, 162, 214, 236, int(90 + 40 * pulse))


def draw_hub(
    menu_font: Font | CrispFont,
    hint_font: Font | CrispFont,
    sprite: Image,
    hub: HubHall,
    player_x: float,
    player_y: float,
    facing: str,
    frame: int,
    elapsed: float,
    cleared_rooms: set[str],
    whisper: str,
    whisper_until: float,
) -> None:
    target = hub_interaction_target(player_x, player_y)

    hub.draw_background()
    draw_hub_clock_hands(elapsed, cleared_rooms)
    hub.draw_shadows(player_x, player_y)
    draw_player(sprite, player_x, player_y, facing, frame)
    hub.apply_lighting()
    # 기억을 복원할수록 홀 전체가 은은하고 따뜻하게 밝아진다.
    if cleared_rooms:
        warmth = min(30, len(cleared_rooms) * 10)
        fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (255, 222, 164, warmth))
    hub.draw_lamp_glints(elapsed)
    draw_hub_gate_effects(elapsed, target, cleared_rooms)

    # 상단 좌측: 로비 이름 + 기억 조각 수집 진행도
    fill(18, 844, 248, 46, (20, 22, 30, 236))
    draw_rectangle(18, 844, 266, 890, 146, 122, 82, filled=False)
    draw_centered_text(hint_font, f"시간의 홀   ·   기억 {len(cleared_rooms)}/3", 142, 867, (239, 209, 158))

    # 상단 3개의 방 명판 (좌: 지하 저장고, 중: 거울의 회랑, 우: 멈춘 시계탑)
    for room_id, title, tile, playable in HUB_DOORS:
        gx = tile_center(*tile)[0]
        is_target = target == room_id
        is_cleared = room_id in cleared_rooms
        if is_cleared:
            border = (242, 206, 118)
            text_color = (252, 232, 174)
            label = f"{title} ★"
        elif playable:
            border = (126, 222, 214) if is_target else (154, 128, 86)
            text_color = (252, 232, 186) if is_target else (228, 204, 162)
            label = title
        else:
            border = (176, 142, 198) if is_target else (94, 94, 112)
            text_color = (214, 198, 228) if is_target else (146, 150, 164)
            label = f"{title} [봉인]"
        fill(gx - 118, 844, 236, 46, (18, 22, 30, 238))
        draw_rectangle(gx - 118, 844, gx + 118, 890, *border, filled=False)
        draw_centered_text(hint_font, label, gx, 867, text_color)

    # 상단 우측: 메뉴 복귀 안내
    fill(1372, 848, 210, 38, (20, 22, 30, 225))
    draw_rectangle(1372, 848, 1582, 886, 86, 108, 118, filled=False)
    draw_centered_text(hint_font, "ESC  메인 메뉴", 1477, 867, (176, 198, 204))

    # 좌·우 상호작용 오브젝트 이름표 (가까울 때 더 밝게)
    diary_x, diary_y = tile_center(*HUB_DIARY_TILE)
    draw_centered_text(
        hint_font, "기억의 일기장", diary_x, diary_y - 36,
        (246, 222, 162) if target == "diary" else (164, 154, 134),
    )
    mirror_x, mirror_y = tile_center(*HUB_MIRROR_PROP_TILE)
    draw_centered_text(
        hint_font, "낡은 거울", mirror_x, mirror_y - 36,
        (194, 232, 244) if target == "mirror_prop" else (144, 162, 176),
    )

    # 대상 근처 플로팅 ENTER 배지 & 하단 안내 문구
    bottom_prompt: str | None = None
    badge_pos: tuple[float, float, str, tuple[int, int, int]] | None = None
    if target == "cellar":
        gx, gy = tile_center(*HUB_CELLAR_DOOR_TILE)
        badge_pos = (gx, gy - 104, "ENTER 입장", (126, 222, 214))
        bottom_prompt = "ENTER 키를 눌러 'Ⅰ. 지하 저장고' 입장"
    elif target == "mirror":
        gx, gy = tile_center(*HUB_MIRROR_DOOR_TILE)
        badge_pos = (gx, gy - 104, "ENTER 입장", (196, 154, 248))
        bottom_prompt = "ENTER 키를 눌러 'Ⅱ. 거울의 회랑' 입장"
    elif target == "clock":
        gx, gy = tile_center(*HUB_CLOCK_DOOR_TILE)
        badge_pos = (gx, gy - 104, "ENTER 입장", (242, 204, 116))
        bottom_prompt = "ENTER 키를 눌러 'Ⅲ. 멈춘 시계탑' 입장"
    elif target == "diary":
        badge_pos = (diary_x, diary_y + 42, "ENTER 읽기", (238, 206, 134))
        bottom_prompt = "ENTER 키를 눌러 '기억의 일기장' 펼치기"
    elif target == "mirror_prop":
        badge_pos = (mirror_x, mirror_y + 42, "ENTER 들여다보기", (164, 218, 238))
        bottom_prompt = "ENTER 키를 눌러 '낡은 거울' 들여다보기"
    elif target == "clock_center":
        badge_pos = (HUB_CENTER_X, HUB_CENTER_Y + 148, "ENTER 확인", (238, 206, 134))
        bottom_prompt = "ENTER 키를 눌러 중앙의 '기억 시계' 확인하기"

    if badge_pos is not None:
        bx, by, btext, bcolor = badge_pos
        bw = 148 if len(btext) > 8 else 124
        fill(bx - bw / 2, by - 14, bw, 28, (18, 26, 34, 236))
        draw_rectangle(bx - bw / 2, by - 14, bx + bw / 2, by + 14, *bcolor, filled=False)
        draw_centered_text(hint_font, btext, bx, by, (242, 240, 228))

    # 오브젝트 조사/봉인 대사 또는 첫 입장 독백
    active_whisper = ""
    if whisper and elapsed < whisper_until:
        active_whisper = whisper
    elif elapsed < 5.8 and target is None:
        if "cellar" in cleared_rooms:
            active_whisper = "\"첫 번째 기억 보석이 빛나고 있어... 기억의 일기장을 펼쳐볼까.\""
        else:
            active_whisper = "\"중앙 시계의 보석이 모두 비어 있다... 먼저 왼쪽 'Ⅰ. 지하 저장고'부터 확인해 보자.\""

    if active_whisper:
        fill(HUB_CENTER_X - 455, 62, 910, 44, (16, 20, 30, 236))
        draw_rectangle(
            HUB_CENTER_X - 455, 62, HUB_CENTER_X + 455, 106,
            168, 142, 94, filled=False,
        )
        draw_centered_text(hint_font, active_whisper, HUB_CENTER_X, 84, (242, 226, 192))

    if bottom_prompt:
        fill(HUB_CENTER_X - 310, 12, 620, 42, (18, 24, 32, 238))
        draw_rectangle(HUB_CENTER_X - 310, 12, HUB_CENTER_X + 310, 54, 136, 214, 208, filled=False)
        draw_centered_text(hint_font, bottom_prompt, HUB_CENTER_X, 33, (239, 218, 172))
    else:
        fill(HUB_CENTER_X - 360, 14, 720, 36, (18, 22, 30, 224))
        draw_rectangle(HUB_CENTER_X - 360, 14, HUB_CENTER_X + 360, 50, 72, 92, 102, filled=False)
        draw_centered_text(
            hint_font,
            "방향키 / WASD 이동   ·   세 개의 문과 일기장·거울 앞에서 ENTER로 상호작용",
            HUB_CENTER_X, 32, (184, 196, 202),
        )


def draw_diary_overlay(
    heading_font: Font | CrispFont,
    menu_font: Font | CrispFont,
    hint_font: Font | CrispFont,
    cleared_rooms: set[str],
) -> None:
    fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (8, 10, 16, 210))
    left, bottom, width, height = 210, 110, 1180, 680
    right, top = left + width, bottom + height
    fill(left, bottom, width, height, (22, 20, 28, 246))
    draw_rectangle(left, bottom, right, top, 178, 146, 94, filled=False)
    draw_rectangle(left + 8, bottom + 8, right - 8, top - 8, 76, 68, 56, filled=False)

    draw_centered_text(heading_font, "기억의 일기장", HUB_CENTER_X, top - 62, (242, 216, 162))
    draw_centered_text(
        hint_font,
        f"복원된 기억 조각   {len(cleared_rooms)} / {len(MEMORY_ENTRIES)}",
        HUB_CENTER_X, top - 108, (142, 208, 210),
    )
    fill(left + 60, top - 128, width - 120, 2, (98, 86, 68))

    card_top = top - 150
    card_h = 138
    card_gap = 20
    for index, (room_id, title, lines, locked_text) in enumerate(MEMORY_ENTRIES):
        cy_top = card_top - index * (card_h + card_gap)
        cy_bottom = cy_top - card_h
        unlocked = room_id in cleared_rooms
        bg = (30, 32, 44, 240) if unlocked else (24, 24, 32, 225)
        border = (196, 164, 102) if unlocked else (72, 74, 88)
        fill(left + 52, cy_bottom, width - 104, card_h, bg)
        draw_rectangle(left + 52, cy_bottom, right - 52, cy_top, *border, filled=False)

        badge_text = "★ 기억 복원됨" if unlocked else "봉인됨"
        badge_color = (128, 232, 198) if unlocked else (136, 140, 154)
        menu_font.draw(left + 78, cy_top - 34, title, (242, 218, 166) if unlocked else (154, 156, 170))
        draw_centered_text(hint_font, badge_text, right - 124, cy_top - 34, badge_color)

        if unlocked:
            hint_font.draw(left + 78, cy_top - 78, lines[0], (232, 226, 214))
            hint_font.draw(left + 78, cy_top - 108, lines[1], (202, 216, 224))
        else:
            hint_font.draw(left + 78, cy_top - 90, locked_text, (132, 138, 152))

    draw_centered_text(
        hint_font,
        "ENTER / SPACE / ESC / 클릭   일기장 덮기",
        HUB_CENTER_X, bottom + 34, (176, 166, 146),
    )


def draw_story_sprite(
    sprite: Image,
    x: float,
    y: float,
    facing: str,
    frame: int,
    size: float,
    tint: tuple[int, int, int] | None = None,
    opacity: float = 1.0,
) -> None:
    if tint is not None:
        pico2d.SDL_SetTextureColorMod(sprite.texture, *tint)
    if opacity < 1.0:
        sprite.opacify(opacity)
    sprite.clip_draw(
        frame * SPRITE_FRAME_SIZE, SPRITE_ROWS[facing],
        SPRITE_FRAME_SIZE, SPRITE_FRAME_SIZE, x, y, size, size,
    )
    if opacity < 1.0:
        sprite.opacify(1.0)
    if tint is not None:
        pico2d.SDL_SetTextureColorMod(sprite.texture, 255, 255, 255)


def draw_story_illustration(sprite: Image, scene_index: int, elapsed: float) -> None:
    cx, cy = SCREEN_WIDTH / 2, 575.0
    pulse = 0.5 + 0.5 * sin(elapsed * 2.4)
    walk_frame = int(elapsed * 5) % 4

    if scene_index == 0:
        # 1장: 어둠 속 희미하게 빛나는 거대한 시계 문양
        for ring in range(3):
            radius = int(128 + ring * 26 + sin(elapsed * 1.8 - ring * 0.9) * 5)
            alpha = max(16, int(52 - ring * 14))
            draw_circle(cx, cy, radius, 96, 178, 186, alpha)
        draw_circle(cx, cy, 118, 16, 24, 38, 235, filled=True)
        draw_circle(cx, cy, 116, 186, 152, 94)
        draw_circle(cx, cy, 102, 82, 128, 138)
        for hour in range(12):
            angle = pi / 2 - hour * (pi / 6)
            inner = 78 if hour % 3 == 0 else 88
            color = (224, 188, 120) if hour % 3 == 0 else (126, 120, 102)
            draw_line(
                cx + cos(angle) * inner, cy + sin(angle) * inner,
                cx + cos(angle) * 98, cy + sin(angle) * 98,
                *color,
            )
        for angle, length, color in (
            (pi / 2 - elapsed * 0.12, 54, (214, 174, 106)),
            (pi / 2 - elapsed * 0.55, 78, (238, 212, 152)),
            (pi / 2 - elapsed * 1.9, 90, (118, 218, 224)),
        ):
            draw_line(cx, cy, cx + cos(angle) * length, cy + sin(angle) * length, *color)
        draw_circle(cx, cy, 8, 228, 190, 118, filled=True)
        draw_story_sprite(sprite, cx, cy - 12, "down", 0, 126, opacity=0.92)
    elif scene_index == 1:
        # 2장: 앞으로 걷는 주인공과 뒤따르는 과거의 그림자 분신들
        fill(cx - 340, cy - 102, 680, 14, (24, 32, 46, 220))
        fill(cx - 340, cy - 88, 680, 2, (92, 134, 142, 150))
        for dot in range(16):
            dx = cx - 220 + dot * 26
            alpha = int(60 + 50 * sin(elapsed * 3.0 - dot * 0.45))
            draw_circle(dx, cy - 58, 3, 108, 212, 224, max(20, alpha), filled=True)
        draw_circle(cx + 150, cy - 4, 72, 240, 184, 98, int(24 + 12 * pulse), filled=True)
        draw_story_sprite(
            sprite, cx - 195, cy - 6, "right", (walk_frame + 2) % 4, 136,
            tint=(208, 147, 255), opacity=0.38,
        )
        draw_story_sprite(
            sprite, cx - 35, cy - 6, "right", (walk_frame + 1) % 4, 146,
            tint=(102, 220, 240), opacity=0.62,
        )
        draw_story_sprite(sprite, cx + 150, cy - 4, "right", walk_frame, 158)
    elif scene_index == 2:
        # 3장: 다가오는 분신과 저 앞의 황금 열쇠
        fill(cx - 340, cy - 102, 680, 14, (26, 28, 40, 220))
        draw_circle(cx - 175, cy - 8, 72 + int(6 * pulse), 224, 116, 128, 36, filled=True)
        draw_circle(cx - 175, cy - 8, 72 + int(6 * pulse), 102, 220, 240, 120)
        draw_story_sprite(
            sprite, cx - 175, cy - 4, "right", walk_frame, 148,
            tint=(102, 220, 240), opacity=0.72,
        )
        draw_story_sprite(sprite, cx + 10, cy - 4, "right", walk_frame, 154)
        for step in range(7):
            lx = cx + 95 + step * 18
            draw_circle(lx, cy - 12, 2, 238, 200, 110, 130, filled=True)
        key_x, key_y = cx + 235, cy - 8 + sin(elapsed * 3.2) * 7
        draw_circle(key_x, key_y, 44, 245, 188, 78, int(30 + 18 * pulse), filled=True)
        draw_circle(key_x, key_y, 26, 255, 214, 110, 80, filled=True)
        draw_circle(key_x - 14, key_y + 3, 12, 255, 224, 128)
        draw_line(key_x - 2, key_y + 3, key_x + 24, key_y + 3, 255, 224, 128)
        draw_line(key_x + 14, key_y + 3, key_x + 14, key_y - 9, 255, 224, 128)
        draw_line(key_x + 23, key_y + 3, key_x + 23, key_y - 12, 255, 224, 128)
    else:
        # 4장: 붉은 융단 너머 빛나는 지하 저장고의 문
        fill(cx - 56, cy - 116, 112, 136, (64, 28, 36))
        fill(cx - 46, cy - 116, 92, 132, (104, 40, 50))
        fill(cx - 42, cy - 116, 2, 132, (182, 142, 82))
        fill(cx + 40, cy - 116, 2, 132, (182, 142, 82))
        # 석조 아치 문과 청록빛 기운
        fill(cx - 88, cy + 4, 176, 124, (44, 48, 60))
        fill(cx - 72, cy + 10, 144, 108, (22, 30, 42))
        draw_rectangle(cx - 88, cy + 4, cx + 88, cy + 128, 168, 140, 92)
        draw_circle(cx, cy + 56, 62, 102, 214, 218, int(34 + 22 * pulse), filled=True)
        draw_circle(cx, cy + 56, 32, 188, 242, 240, int(52 + 24 * pulse), filled=True)
        for bar in (-50, -34, 34, 50):
            fill(cx + bar, cy + 12, 4, 104, (110, 122, 134))
        draw_story_sprite(sprite, cx, cy - 68, "up", 0, 138)


def draw_story(
    menu_font: Font | CrispFont,
    hint_font: Font | CrispFont,
    sprite: Image,
    scene_index: int,
    scene_elapsed: float,
    total_elapsed: float,
    reveal_all: bool,
) -> None:
    clear_canvas()
    # 깊은 밤하늘과 은은한 시간의 입자 배경
    fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (8, 13, 23))
    for band_y, color in (
        (540, (10, 17, 30)),
        (660, (12, 21, 36)),
        (780, (15, 25, 42)),
    ):
        fill(0, band_y, SCREEN_WIDTH, 120, color)

    for mote in range(18):
        mx = (mote * 97 + sin(total_elapsed * 0.4 + mote) * 28) % SCREEN_WIDTH
        my = (mote * 53 + total_elapsed * (10 + mote % 5)) % SCREEN_HEIGHT
        alpha = int(45 + 35 * sin(total_elapsed * 2.0 + mote * 1.3))
        fill(mx, my, 3, 3, (148, 198, 206, max(12, alpha)))

    chapter, lines = INTRO_SCENES[scene_index]

    # 상단 장 제목
    draw_centered_text(hint_font, chapter, SCREEN_WIDTH / 2, 816, (152, 196, 198))
    fill(540, 794, 180, 2, (62, 98, 106))
    fill(880, 794, 180, 2, (62, 98, 106))
    fill(794, 789, 12, 12, (186, 152, 96))

    # 장면 일러스트
    draw_story_illustration(sprite, scene_index, total_elapsed)

    # 하단 스토리 대사창
    box_left, box_bottom, box_width, box_height = 200, 146, 1200, 192
    fill(box_left, box_bottom, box_width, box_height, (13, 20, 32, 238))
    draw_rectangle(
        box_left, box_bottom, box_left + box_width, box_bottom + box_height,
        142, 124, 90, filled=False,
    )
    draw_rectangle(
        box_left + 6, box_bottom + 6,
        box_left + box_width - 6, box_bottom + box_height - 6,
        52, 82, 92, filled=False,
    )

    total_chars = sum(len(line) for line in lines)
    visible_chars = total_chars if reveal_all else int(scene_elapsed * STORY_TYPE_SPEED)
    remaining = visible_chars
    line_y = (272, 212)
    line_colors = ((242, 230, 202), (212, 218, 224))
    for text, y, color in zip(lines, line_y, line_colors):
        shown = text[: max(0, remaining)]
        remaining -= len(text)
        if shown:
            draw_centered_text(menu_font, shown, SCREEN_WIDTH / 2, y, color)

    if visible_chars >= total_chars:
        blink = 0.5 + 0.5 * sin(total_elapsed * 5.0)
        prompt_text = "시작하기 ▶" if scene_index == len(INTRO_SCENES) - 1 else "다음 ▶"
        draw_centered_text(
            hint_font, prompt_text, box_left + box_width - 78, box_bottom + 28,
            (int(160 + 80 * blink), int(205 + 35 * blink), int(200 + 30 * blink)),
        )

    # 장면 진행 점 (● ○ ○ ○)
    dot_spacing = 28
    dots_start_x = SCREEN_WIDTH / 2 - (len(INTRO_SCENES) - 1) * dot_spacing / 2
    for index in range(len(INTRO_SCENES)):
        dx = dots_start_x + index * dot_spacing
        if index == scene_index:
            draw_circle(dx, 98, 6, 226, 190, 120, filled=True)
        elif index < scene_index:
            draw_circle(dx, 98, 5, 112, 178, 184, filled=True)
        else:
            draw_circle(dx, 98, 5, 76, 98, 112)

    draw_centered_text(
        hint_font,
        "ENTER / SPACE / 클릭  다음     ·     ESC  건너뛰기",
        SCREEN_WIDTH / 2, 48, (132, 162, 170),
    )

    # 장면 전환 페이드 인
    if scene_elapsed < STORY_FADE_DURATION:
        fade_alpha = int(255 * (1.0 - scene_elapsed / STORY_FADE_DURATION))
        fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (6, 10, 18, fade_alpha))


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


def volume_from_mouse_x(x: float) -> int:
    ratio = (x - VOLUME_BAR_LEFT) / (VOLUME_BAR_RIGHT - VOLUME_BAR_LEFT)
    ratio = max(0.0, min(1.0, ratio))
    return int(round(ratio * 10)) * VOLUME_STEP


def draw_volume_button(
    menu_font: Font | CrispFont,
    hint_font: Font | CrispFont,
    label: str,
    volume: int,
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

    label_color = (239, 222, 186) if selected else (171, 186, 197)
    menu_font.draw(left + 32, y, label, label_color)

    # 볼륨 게이지 바
    bar_width = VOLUME_BAR_RIGHT - VOLUME_BAR_LEFT
    bar_height = 14
    fill(VOLUME_BAR_LEFT, y - bar_height / 2, bar_width, bar_height, (9, 18, 30))
    draw_rectangle(
        VOLUME_BAR_LEFT, y - bar_height / 2,
        VOLUME_BAR_RIGHT, y + bar_height / 2,
        68, 106, 116 if selected else 84, filled=False,
    )
    filled_w = int(bar_width * volume / 100)
    if filled_w > 0:
        bar_color = (112, 212, 208) if selected else (76, 154, 160)
        fill(VOLUME_BAR_LEFT + 1, y - bar_height / 2 + 1, max(1, filled_w - 2), bar_height - 2, bar_color)
    # 10% 눈금 표시
    for step in range(1, 10):
        tx = VOLUME_BAR_LEFT + bar_width * step / 10
        draw_line(tx, y - bar_height / 2 + 2, tx, y + bar_height / 2 - 2, 18, 34, 48)
    # 슬라이더 손잡이
    knob_x = VOLUME_BAR_LEFT + bar_width * volume / 100
    knob_color = (238, 204, 128) if selected else (164, 178, 188)
    fill(knob_x - 5, y - 12, 10, 24, knob_color)
    draw_rectangle(knob_x - 5, y - 12, knob_x + 5, y + 12, 18, 28, 40, filled=False)

    value_text = f"{volume}%" if volume > 0 else "꺼짐"
    value_color = (239, 222, 186) if (selected and volume > 0) else (
        (146, 158, 168) if volume == 0 else (186, 204, 212)
    )
    draw_centered_text(hint_font, value_text, right - 68, y, value_color)
    if selected:
        draw_centered_text(hint_font, "◀", VOLUME_BAR_LEFT - 18, y, (132, 198, 198))
        draw_centered_text(hint_font, "▶", VOLUME_BAR_RIGHT + 18, y, (132, 198, 198))


def draw_settings(
    heading_font: Font | CrispFont,
    menu_font: Font | CrispFont,
    hint_font: Font | CrispFont,
    selected_item: int,
    bgm_volume: int,
    sfx_volume: int,
    fullscreen: bool,
    sprite: Image,
    over_game: bool,
) -> None:
    if over_game:
        draw_rectangle(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 3, 8, 15, 64, filled=True)
        draw_rectangle(300, 42, 920, 775, 12, 24, 36, 196, filled=True)
        draw_rectangle(300, 42, 920, 775, 72, 114, 120, filled=False)
    else:
        draw_menu_background(sprite)
    draw_centered_text(
        heading_font, "설정", 610, 697, (238, 221, 185)
    )
    draw_volume_button(
        menu_font, hint_font, "배경음악", bgm_volume,
        SETTINGS_ITEM_Y[0], selected_item == 0, MENU_BUTTON_CENTER_X,
    )
    draw_volume_button(
        menu_font, hint_font, "효과음", sfx_volume,
        SETTINGS_ITEM_Y[1], selected_item == 1, MENU_BUTTON_CENTER_X,
    )
    draw_menu_button(
        menu_font,
        f"화면 모드   {'전체화면' if fullscreen else '창화면 (1280 x 720)'}",
        SETTINGS_ITEM_Y[2], selected_item == 2, MENU_BUTTON_CENTER_X,
    )
    draw_menu_button(
        menu_font, "돌아가기",
        SETTINGS_ITEM_Y[3], selected_item == 3, MENU_BUTTON_CENTER_X,
    )
    draw_menu_footer(
        hint_font, "◀/▶ · 드래그 음량 조절   ·   ENTER 음소거   ·   ESC 돌아가기"
    )


def draw_pause_overlay(
    menu_font: Font | CrispFont,
    hint_font: Font | CrispFont,
    selected_item: int,
) -> None:
    draw_rectangle(
        0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 3, 8, 15, 96, filled=True
    )
    panel_left, panel_bottom = 300, 165
    panel_right, panel_top = 920, 640
    draw_rectangle(
        panel_left, panel_bottom, panel_right, panel_top,
        12, 24, 36, 212, filled=True,
    )
    draw_rectangle(
        panel_left, panel_bottom, panel_right, panel_top,
        75, 120, 124, filled=False,
    )
    draw_centered_text(
        menu_font, "일시정지", (panel_left + panel_right) / 2, 576,
        (238, 221, 185),
    )
    for index, (label, y) in enumerate(PAUSE_ITEMS):
        draw_menu_button(
            menu_font, label, y, index == selected_item, MENU_BUTTON_CENTER_X
        )
    draw_centered_text(
        hint_font, "ESC  계속하기", (panel_left + panel_right) / 2, 198,
        (132, 166, 174),
    )


def main() -> None:
    open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT)
    pico2d.SDL_SetRenderDrawBlendMode(pico2d_core.renderer, pico2d.SDL_BLENDMODE_BLEND)
    set_display_mode(fullscreen=False)
    fonts_dir = Path(environ["WINDIR"]) / "Fonts"
    title_font = CrispFont(str(fonts_dir / "georgiab.ttf"), 68)
    korean_bold = str(fonts_dir / "malgunbd.ttf")
    menu_font = CrispFont(korean_bold, 30)
    heading_font = CrispFont(korean_bold, 46)
    hint_font = CrispFont(korean_bold, 18)
    assets = resource_root() / "assets"
    sprite = load_image(str(assets / "player_sprite.png"))
    props = load_image(str(assets / "cellar_props.png"))
    pico2d.SDL_SetTextureScaleMode(props.texture, pico2d.SDL_ScaleModeNearest)
    monster_sprites = {
        kind: load_image(str(assets / f"cellar_{kind}.png")) for kind in MONSTER_ART
    }
    for monster_sprite in monster_sprites.values():
        pico2d.SDL_SetTextureScaleMode(monster_sprite.texture, pico2d.SDL_ScaleModeNearest)
    hub = HubHall(props)
    cellar = Cellar(props)
    run = CellarRun()
    mirror_run = MirrorHallRun()
    clock_run = ClockTowerRun()
    sounds = SoundBank(assets / "sounds")
    effects = EffectsManager()
    held_keys: set[int] = set()
    previous_time = perf_counter()
    running = True
    screen = "menu"
    pause_menu_open = False
    pause_return_screen = "game"
    hub_x, hub_y = HUB_START
    hub_vx = hub_vy = 0.0
    hub_facing, hub_frame = "up", 0
    hub_animation_time = 0.0
    hub_elapsed = 0.0
    hub_whisper = ""
    hub_whisper_until = 0.0
    cleared_rooms: set[str] = set()
    last_hub_frame = 0
    last_game_frame = 0
    ghost_mote_timer = 0.0
    story_scene = 0
    story_scene_elapsed = 0.0
    story_total_elapsed = 0.0
    story_reveal_all = False
    last_story_chars = 0
    selected_menu_item = 0
    selected_settings_item = 0
    selected_pause_item = 0
    dragging_volume_item: int | None = None
    fullscreen = False
    sounds.play_bgm("hub")

    def enter_hub() -> None:
        nonlocal screen, hub_x, hub_y, hub_vx, hub_vy
        nonlocal hub_facing, hub_frame, hub_animation_time, hub_elapsed, last_hub_frame
        nonlocal hub_whisper, hub_whisper_until
        screen = "hub"
        hub_x, hub_y = HUB_START
        hub_vx = hub_vy = 0.0
        hub_facing, hub_frame = "up", 0
        hub_animation_time = 0.0
        hub_elapsed = 0.0
        hub_whisper = ""
        hub_whisper_until = 0.0
        last_hub_frame = 0
        effects.clear()
        sounds.set_paused_duck(False)
        sounds.play_bgm("hub")
        held_keys.clear()

    def start_story() -> None:
        nonlocal screen, story_scene, story_scene_elapsed
        nonlocal story_total_elapsed, story_reveal_all, last_story_chars
        screen = "story"
        story_scene = 0
        story_scene_elapsed = 0.0
        story_total_elapsed = 0.0
        story_reveal_all = False
        last_story_chars = 0
        sounds.play_bgm("hub")
        held_keys.clear()

    def advance_story() -> None:
        nonlocal story_scene, story_scene_elapsed, story_reveal_all, last_story_chars
        _, lines = INTRO_SCENES[story_scene]
        total_chars = sum(len(line) for line in lines)
        if not story_reveal_all and int(story_scene_elapsed * STORY_TYPE_SPEED) < total_chars:
            story_reveal_all = True
            last_story_chars = total_chars
            sounds.play("ui_move")
            return
        sounds.play("ui_confirm")
        if story_scene + 1 < len(INTRO_SCENES):
            story_scene += 1
            story_scene_elapsed = 0.0
            story_reveal_all = False
            last_story_chars = 0
        else:
            enter_hub()

    def handle_mirror_events() -> None:
        for kind, ex, ey in mirror_run.events:
            if kind == "step":
                sounds.play("step")
            elif kind == "switch":
                sounds.play("ui_confirm")
                effects.rings.append(ShockRing(ex, ey, 10, 74, 0.38, (124, 232, 226)))
            elif kind == "key":
                sounds.play("key")
                effects.burst_key(ex, ey)
            elif kind in ("trap", "out_of_moves"):
                sounds.play("ghost_hit")
                effects.burst_ghost_hit(ex, ey)
            elif kind == "next":
                sounds.play("round_clear")
                effects.burst_round_clear(ex, ey)
            elif kind == "clear":
                sounds.play("stage_clear")
                effects.burst_round_clear(ex, ey)
        mirror_run.events.clear()

    def handle_run_events() -> None:
        for kind, ex, ey in run.events:
            if kind == "key":
                sounds.play("key")
                effects.burst_key(ex, ey)
            elif kind == "key_shift":
                sounds.play("ui_move")
                effects.rings.append(ShockRing(ex, ey, 10, 68, 0.45, (255, 214, 108)))
            elif kind == "monster":
                sounds.play("monster_hit")
                effects.burst_monster_hit(ex, ey)
            elif kind in ("ghost", "timeout"):
                sounds.play("ghost_hit")
                effects.burst_ghost_hit(ex, ey)
            elif kind == "next":
                sounds.play("round_clear")
                effects.burst_round_clear(ex, ey)
            elif kind == "clear":
                sounds.play("stage_clear")
                effects.burst_round_clear(ex, ey)
                sounds.play_bgm("hub")
        run.events.clear()

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
                        sounds.play("ui_move")
                        dragging_volume_item = None
                        if pause_menu_open:
                            screen = "pause"
                        else:
                            screen = "menu"
                    elif screen in ("game", "mirror", "clock"):
                        sounds.play("ui_move")
                        pause_return_screen = screen
                        screen = "pause"
                        selected_pause_item = 0
                        pause_menu_open = True
                        sounds.set_paused_duck(True)
                        held_keys.clear()
                    elif screen == "pause":
                        sounds.play("ui_move")
                        screen = pause_return_screen
                        pause_menu_open = False
                        sounds.set_paused_duck(False)
                    elif screen in ("clear", "mirror_clear"):
                        sounds.play("ui_move")
                        screen = "menu"
                        sounds.play_bgm("hub")
                    elif screen == "diary":
                        sounds.play("ui_move")
                        screen = "hub"
                    elif screen == "story":
                        sounds.play("ui_move")
                        enter_hub()
                    elif screen == "hub":
                        sounds.play("ui_move")
                        screen = "menu"
                        held_keys.clear()
                    else:
                        running = False
                elif screen == "diary" and event.key in (
                    SDLK_RETURN, SDLK_KP_ENTER, SDLK_SPACE
                ):
                    sounds.play("ui_move")
                    screen = "hub"
                elif screen == "story" and event.key in (
                    SDLK_RETURN, SDLK_KP_ENTER, SDLK_SPACE
                ):
                    advance_story()
                elif screen in ("clear", "mirror_clear") and event.key in (SDLK_RETURN, SDLK_KP_ENTER):
                    sounds.play("ui_confirm")
                    enter_hub()
                elif screen == "hub" and event.key in (SDLK_RETURN, SDLK_KP_ENTER):
                    target = hub_interaction_target(hub_x, hub_y)
                    if target == "cellar":
                        sounds.play("ui_confirm")
                        screen = "game"
                        run.reset("열쇠를 찾아 북동쪽 철문으로 가세요.")
                        effects.clear()
                        last_game_frame = 0
                        sounds.set_paused_duck(False)
                        sounds.play_bgm("cellar")
                        held_keys.clear()
                    elif target == "mirror":
                        sounds.play("ui_confirm")
                        screen = "mirror"
                        mirror_run.reset_all()
                        effects.clear()
                        sounds.set_paused_duck(False)
                        sounds.play_bgm("hub")
                        held_keys.clear()
                    elif target == "clock":
                        sounds.play("ui_confirm")
                        screen = "clock"
                        clock_run.reset_all()
                        effects.clear()
                        sounds.set_paused_duck(False)
                        sounds.play_bgm("cellar")
                        held_keys.clear()
                    elif target == "diary":
                        sounds.play("ui_confirm")
                        screen = "diary"
                        held_keys.clear()
                    elif target == "mirror_prop":
                        sounds.play("ui_move")
                        if "cellar" in cleared_rooms:
                            hub_whisper = "\"지하 저장고를 빠져나오고 나니, 거울 속 내 눈빛이 조금 더 선명해졌다.\""
                        else:
                            hub_whisper = "\"거울 속 내 얼굴이 흐릿하다... 등에 멘 시계 가방의 초침만 또렷이 비친다.\""
                        hub_whisper_until = hub_elapsed + 4.5
                    elif target == "clock_center":
                        sounds.play("ui_move")
                        if len(cleared_rooms) == 0:
                            hub_whisper = "\"기억 시계의 보석 칸이 모두 비어 있다. 세 방의 기억을 되찾아야 한다.\""
                        elif len(cleared_rooms) < len(MEMORY_ENTRIES):
                            hub_whisper = f"\"기억 보석 {len(cleared_rooms)}/{len(MEMORY_ENTRIES)}개가 밝혀졌다. 남은 방의 기억을 더 찾아보자.\""
                        else:
                            hub_whisper = "\"모든 기억 보석이 빛나고 있다! 중앙 시계가 나를 부르는 것 같다.\""
                        hub_whisper_until = hub_elapsed + 4.5
                elif screen == "game" and event.key in (SDLK_RETURN, SDLK_KP_ENTER):
                    if run.near_test_door():
                        result = run.complete_round()
                        handle_run_events()
                        held_keys.clear()
                        delta_time = 0.0
                        if result == "clear":
                            cleared_rooms.add("cellar")
                            screen = "clear"
                elif screen == "clock" and event.key == SDLK_r:
                    sounds.play("ui_move")
                    clock_run.begin_round("시계판 위치를 초기화했습니다.")
                    held_keys.clear()
                elif screen == "clock" and event.key in KEY_DIRECTIONS:
                    held_keys.add(event.key)
                elif screen == "mirror" and event.key == SDLK_r:
                    sounds.play("ui_move")
                    mirror_run.begin_stage("현재 스테이지를 처음부터 다시 시작합니다.")
                    held_keys.clear()
                elif screen == "mirror" and event.key in KEY_DIRECTIONS:
                    held_keys.add(event.key)
                    dx, dy = KEY_DIRECTIONS[event.key]
                    res = mirror_run.try_step(dx, dy)
                    handle_mirror_events()
                    if res == "reset":
                        held_keys.clear()
                    elif res == "clear":
                        cleared_rooms.add("mirror")
                        held_keys.clear()
                        screen = "mirror_clear"
                elif screen == "game" and event.key in KEY_DIRECTIONS:
                    held_keys.add(event.key)
                elif screen == "hub" and event.key in KEY_DIRECTIONS:
                    held_keys.add(event.key)
                elif screen == "menu" and event.key in (SDLK_UP, SDLK_w):
                    selected_menu_item = (selected_menu_item - 1) % 3
                    sounds.play("ui_move")
                elif screen == "menu" and event.key in (SDLK_DOWN, SDLK_s):
                    selected_menu_item = (selected_menu_item + 1) % 3
                    sounds.play("ui_move")
                elif screen == "pause" and event.key in (SDLK_UP, SDLK_w):
                    selected_pause_item = (selected_pause_item - 1) % len(PAUSE_ITEMS)
                    sounds.play("ui_move")
                elif screen == "pause" and event.key in (SDLK_DOWN, SDLK_s):
                    selected_pause_item = (selected_pause_item + 1) % len(PAUSE_ITEMS)
                    sounds.play("ui_move")
                elif screen == "settings" and event.key in (SDLK_UP, SDLK_w):
                    selected_settings_item = (selected_settings_item - 1) % len(SETTINGS_ITEM_Y)
                    sounds.play("ui_move")
                elif screen == "settings" and event.key in (SDLK_DOWN, SDLK_s):
                    selected_settings_item = (selected_settings_item + 1) % len(SETTINGS_ITEM_Y)
                    sounds.play("ui_move")
                elif screen == "menu" and event.key in (SDLK_RETURN, SDLK_KP_ENTER):
                    sounds.play("ui_confirm")
                    if selected_menu_item == 0:
                        start_story()
                    elif selected_menu_item == 1:
                        running = False
                    else:
                        pause_menu_open = False
                        screen = "settings"
                elif screen == "pause" and event.key in (SDLK_RETURN, SDLK_KP_ENTER):
                    sounds.play("ui_confirm")
                    if selected_pause_item == 0:
                        pause_menu_open = False
                        enter_hub()
                    elif selected_pause_item == 1:
                        pause_menu_open = True
                        screen = "settings"
                    else:
                        running = False
                elif screen == "settings" and event.key in (
                    SDLK_LEFT, SDLK_a, SDLK_RIGHT, SDLK_d, SDLK_RETURN, SDLK_KP_ENTER
                ):
                    delta_vol = -VOLUME_STEP if event.key in (SDLK_LEFT, SDLK_a) else (
                        VOLUME_STEP if event.key in (SDLK_RIGHT, SDLK_d) else 0
                    )
                    if selected_settings_item == 0:
                        if delta_vol:
                            sounds.set_bgm_volume(sounds.bgm_volume + delta_vol)
                            sounds.play("ui_move")
                        else:
                            sounds.toggle_bgm_mute()
                            sounds.play("ui_confirm")
                    elif selected_settings_item == 1:
                        if delta_vol:
                            sounds.set_sfx_volume(sounds.sfx_volume + delta_vol)
                            sounds.play("ui_move")
                        else:
                            sounds.toggle_sfx_mute()
                            sounds.play("ui_confirm")
                    elif selected_settings_item == 2:
                        fullscreen = not fullscreen
                        set_display_mode(fullscreen)
                        sounds.play("ui_confirm")
                    else:
                        sounds.play("ui_move")
                        dragging_volume_item = None
                        screen = "pause" if pause_menu_open else "menu"
            elif event.type == SDL_MOUSEMOTION and screen in ("menu", "settings"):
                mouse_x, mouse_y = mouse_event_to_canvas_position(event.x, event.y)
                if screen == "settings" and dragging_volume_item is not None:
                    new_vol = volume_from_mouse_x(mouse_x)
                    if dragging_volume_item == 0 and new_vol != sounds.bgm_volume:
                        sounds.set_bgm_volume(new_vol)
                        sounds.play("ui_move")
                    elif dragging_volume_item == 1 and new_vol != sounds.sfx_volume:
                        sounds.set_sfx_volume(new_vol)
                        sounds.play("ui_move")
                else:
                    hovered_item = menu_item_at(screen, mouse_x, mouse_y)
                    if hovered_item is not None:
                        if screen == "menu":
                            if selected_menu_item != hovered_item:
                                selected_menu_item = hovered_item
                                sounds.play("ui_move")
                        else:
                            if selected_settings_item != hovered_item:
                                selected_settings_item = hovered_item
                                sounds.play("ui_move")
            elif event.type == SDL_MOUSEBUTTONUP and event.button == SDL_BUTTON_LEFT:
                dragging_volume_item = None
            elif event.type == SDL_MOUSEMOTION and screen == "pause":
                mouse_x, mouse_y = mouse_event_to_canvas_position(event.x, event.y)
                hovered_item = menu_item_at(screen, mouse_x, mouse_y)
                if hovered_item is not None and selected_pause_item != hovered_item:
                    selected_pause_item = hovered_item
                    sounds.play("ui_move")
            elif (
                event.type == SDL_MOUSEBUTTONDOWN
                and event.button == SDL_BUTTON_LEFT
                and screen == "diary"
            ):
                sounds.play("ui_move")
                screen = "hub"
            elif (
                event.type == SDL_MOUSEBUTTONDOWN
                and event.button == SDL_BUTTON_LEFT
                and screen == "story"
            ):
                advance_story()
            elif (
                event.type == SDL_MOUSEBUTTONDOWN
                and event.button == SDL_BUTTON_LEFT
                and screen in ("menu", "settings", "pause")
            ):
                mouse_x, mouse_y = mouse_event_to_canvas_position(event.x, event.y)
                clicked_item = menu_item_at(screen, mouse_x, mouse_y)
                if clicked_item is not None and screen == "menu":
                    selected_menu_item = clicked_item
                    sounds.play("ui_confirm")
                    if clicked_item == 0:
                        start_story()
                    elif clicked_item == 1:
                        running = False
                    else:
                        pause_menu_open = False
                        screen = "settings"
                elif clicked_item is not None and screen == "pause":
                    selected_pause_item = clicked_item
                    sounds.play("ui_confirm")
                    if clicked_item == 0:
                        pause_menu_open = False
                        enter_hub()
                    elif clicked_item == 1:
                        pause_menu_open = True
                        screen = "settings"
                    else:
                        running = False
                elif clicked_item is not None:
                    selected_settings_item = clicked_item
                    if clicked_item in (0, 1):
                        if VOLUME_BAR_LEFT - 14 <= mouse_x <= VOLUME_BAR_RIGHT + 14:
                            dragging_volume_item = clicked_item
                            new_vol = volume_from_mouse_x(mouse_x)
                            if clicked_item == 0:
                                sounds.set_bgm_volume(new_vol)
                            else:
                                sounds.set_sfx_volume(new_vol)
                            sounds.play("ui_move")
                        elif mouse_x < VOLUME_BAR_LEFT - 14:
                            if clicked_item == 0:
                                sounds.toggle_bgm_mute()
                            else:
                                sounds.toggle_sfx_mute()
                            sounds.play("ui_confirm")
                        else:
                            if clicked_item == 0:
                                sounds.set_bgm_volume(sounds.bgm_volume + VOLUME_STEP)
                            else:
                                sounds.set_sfx_volume(sounds.sfx_volume + VOLUME_STEP)
                            sounds.play("ui_move")
                    elif clicked_item == 2:
                        fullscreen = not fullscreen
                        set_display_mode(fullscreen)
                        sounds.play("ui_confirm")
                    else:
                        sounds.play("ui_move")
                        dragging_volume_item = None
                        screen = "pause" if pause_menu_open else "menu"
            elif event.type == SDL_KEYUP and event.key in KEY_DIRECTIONS:
                held_keys.discard(event.key)

        if screen == "story":
            story_scene_elapsed += delta_time
            story_total_elapsed += delta_time
            if not story_reveal_all:
                _, lines = INTRO_SCENES[story_scene]
                full_text = "".join(lines)
                shown_count = min(len(full_text), int(story_scene_elapsed * STORY_TYPE_SPEED))
                if shown_count - last_story_chars >= 2:
                    if full_text[shown_count - 1] != " ":
                        sounds.play("story_tick")
                    last_story_chars = shown_count

        if screen == "hub":
            hub_elapsed += delta_time
            move_x = sum(KEY_DIRECTIONS[key][0] for key in held_keys)
            move_y = sum(KEY_DIRECTIONS[key][1] for key in held_keys)
            direction_length = hypot(move_x, move_y)
            if direction_length:
                target_x = move_x / direction_length * HUB_SPEED
                target_y = move_y / direction_length * HUB_SPEED
            else:
                target_x = target_y = 0.0
            acceleration = PLAYER_ACCELERATION if direction_length else PLAYER_STOP_ACCELERATION
            hub_vx = (
                min(target_x, hub_vx + acceleration * delta_time)
                if hub_vx < target_x
                else max(target_x, hub_vx - acceleration * delta_time)
            )
            hub_vy = (
                min(target_y, hub_vy + acceleration * delta_time)
                if hub_vy < target_y
                else max(target_y, hub_vy - acceleration * delta_time)
            )
            previous_hub = hub_x, hub_y
            hub_x, hub_y = move_player(
                hub_x, hub_y, hub_vx, hub_vy, delta_time,
                tile_map=HUB_MAP, max_speed=HUB_SPEED,
            )
            if (hub_x, hub_y) != previous_hub:
                if abs(move_x) > abs(move_y):
                    hub_facing = "right" if move_x > 0 else "left"
                elif move_y != 0:
                    hub_facing = "up" if move_y > 0 else "down"
                hub_animation_time += delta_time
                hub_frame = int(hub_animation_time * 8) % 4
                if hub_frame != last_hub_frame and hub_frame in (1, 3):
                    sounds.play("step")
                last_hub_frame = hub_frame
            else:
                hub_frame = 0
                last_hub_frame = 0

        if screen == "clock":
            move_x = sum(KEY_DIRECTIONS[key][0] for key in held_keys)
            move_y = sum(KEY_DIRECTIONS[key][1] for key in held_keys)
            clock_run.update(move_x, move_y, delta_time)
            for kind, ex, ey in clock_run.events:
                if kind == "step":
                    sounds.play("step")
                    effects.spawn_dust(ex, ey)
            clock_run.events.clear()
            effects.update(delta_time)

        if screen == "mirror":
            move_x = sum(KEY_DIRECTIONS[key][0] for key in held_keys)
            move_y = sum(KEY_DIRECTIONS[key][1] for key in held_keys)
            res = mirror_run.update(move_x, move_y, delta_time)
            handle_mirror_events()
            effects.update(delta_time)
            if res == "reset":
                held_keys.clear()
            elif res == "clear":
                cleared_rooms.add("mirror")
                held_keys.clear()
                screen = "mirror_clear"

        if screen == "game":
            move_x = sum(KEY_DIRECTIONS[key][0] for key in held_keys)
            move_y = sum(KEY_DIRECTIONS[key][1] for key in held_keys)
            prev_pos = (run.x, run.y)
            result = run.update(move_x, move_y, delta_time)
            handle_run_events()
            if (run.x, run.y) != prev_pos and run.frame != last_game_frame and run.frame in (1, 3):
                sounds.play("step")
                effects.spawn_dust(run.x, run.y)
            last_game_frame = run.frame
            ghost_mote_timer += delta_time
            if ghost_mote_timer >= 0.14:
                ghost_mote_timer = 0.0
                for ghost in run.ghosts:
                    mote_color = (208, 147, 255) if ghost.mirrored else (102, 220, 240)
                    effects.spawn_dust(ghost.pose.x, ghost.pose.y, mote_color)
            effects.update(delta_time)
            if result != "playing":
                held_keys.clear()
            if result == "clear":
                cleared_rooms.add("cellar")
                screen = "clear"

        show_cellar = (
            screen in ("game", "clear")
            or (screen == "pause" and pause_return_screen == "game")
            or (screen == "settings" and pause_menu_open and pause_return_screen == "game")
        )
        show_mirror = (
            screen in ("mirror", "mirror_clear")
            or (screen == "pause" and pause_return_screen == "mirror")
            or (screen == "settings" and pause_menu_open and pause_return_screen == "mirror")
        )

        show_clock = (
            screen == "clock"
            or (screen == "pause" and pause_return_screen == "clock")
            or (screen == "settings" and pause_menu_open and pause_return_screen == "clock")
        )

        if show_clock:
            draw_clock_tower(menu_font, hint_font, draw_centered_text, sprite, clock_run)
            effects.draw_world()
            effects.draw_overlay()

        if show_mirror:
            shake_x, shake_y = effects.shake_offset() if screen == "mirror" else (0, 0)
            if shake_x or shake_y:
                clear_canvas()
                viewport = pico2d.SDL_Rect(shake_x, shake_y, SCREEN_WIDTH, SCREEN_HEIGHT)
                pico2d.SDL_RenderSetViewport(pico2d_core.renderer, ctypes.byref(viewport))
            draw_mirror_hall(menu_font, hint_font, draw_centered_text, sprite, mirror_run)
            effects.draw_world()
            if shake_x or shake_y:
                pico2d.SDL_RenderSetViewport(pico2d_core.renderer, None)
            effects.draw_overlay()

        if show_cellar:
            shake_x, shake_y = effects.shake_offset() if screen == "game" else (0, 0)
            if shake_x or shake_y:
                clear_canvas()
                viewport = pico2d.SDL_Rect(shake_x, shake_y, SCREEN_WIDTH, SCREEN_HEIGHT)
                pico2d.SDL_RenderSetViewport(pico2d_core.renderer, ctypes.byref(viewport))
            cellar.draw_background()
            cellar.draw_shadows(run.x, run.y)
            draw_player(sprite, run.x, run.y, run.facing, run.frame)
            cellar.apply_lighting()
            cellar.draw_lamp_glints(run.elapsed)
            draw_ghost_trails(run)
            draw_test_door(hint_font, run.near_test_door())
            for monster in run.monsters:
                draw_monster(monster_sprites[monster.kind], monster)
            for ghost in run.ghosts:
                draw_ghost(sprite, ghost)
            if not run.has_key:
                draw_key(*tile_center(*run.key_tile), run.elapsed)
            draw_player_status_effects(run)
            effects.draw_world()
            if shake_x or shake_y:
                pico2d.SDL_RenderSetViewport(pico2d_core.renderer, None)
            effects.draw_overlay()
            draw_run_hud(menu_font, hint_font, run)

        if screen == "pause":
            draw_pause_overlay(menu_font, hint_font, selected_pause_item)
        elif screen == "story":
            draw_story(
                menu_font, hint_font, sprite,
                story_scene, story_scene_elapsed, story_total_elapsed, story_reveal_all,
            )
        elif screen in ("hub", "diary"):
            draw_hub(
                menu_font, hint_font, sprite, hub,
                hub_x, hub_y, hub_facing, hub_frame, hub_elapsed,
                cleared_rooms, hub_whisper, hub_whisper_until,
            )
            if screen == "diary":
                draw_diary_overlay(heading_font, menu_font, hint_font, cleared_rooms)
        elif screen == "settings":
            draw_settings(
                heading_font, menu_font, hint_font, selected_settings_item,
                sounds.bgm_volume, sounds.sfx_volume, fullscreen, sprite, pause_menu_open,
            )
        elif screen == "menu":
            draw_menu(
                title_font, menu_font, hint_font, selected_menu_item, sprite
            )
        elif screen == "mirror_clear":
            fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (10, 12, 20, 210))
            fill(230, 250, 1140, 400, (18, 18, 34, 242))
            draw_rectangle(230, 250, 1370, 650, 196, 158, 242, filled=False)
            draw_rectangle(238, 258, 1362, 642, 92, 78, 132, filled=False)
            draw_centered_text(hint_font, f"두 번째 기억 조각 복원됨   ({len(cleared_rooms)} / 3)", 800, 604, (206, 166, 252))
            draw_centered_text(heading_font, "거울의 회랑 통과", 800, 544, (239, 209, 158))
            draw_centered_text(
                menu_font,
                "\"피해야 할 그림자가 아니라, 함께 나아가야 할 나의 조각이었다.\"",
                800, 464, (242, 230, 202),
            )
            draw_centered_text(
                hint_font,
                "시간의 홀 중앙 시계에 두 번째 보석이 밝혀졌습니다.  로비의 '기억의 일기장'을 확인해 보세요!",
                800, 396, (206, 186, 238),
            )
            draw_centered_text(
                hint_font,
                f"5라운드 클리어 (총 {mirror_run.total_moves}회 이동)     ·     ENTER  시간의 홀로     ·     ESC  메인 메뉴",
                800, 304, (205, 188, 163),
            )
        elif screen == "clear":
            fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (10, 12, 20, 210))
            fill(230, 250, 1140, 400, (15, 21, 33, 242))
            draw_rectangle(230, 250, 1370, 650, 192, 158, 98, filled=False)
            draw_rectangle(238, 258, 1362, 642, 62, 98, 108, filled=False)
            draw_centered_text(hint_font, "첫 번째 기억 조각 복원됨   (1 / 3)", 800, 604, (132, 232, 206))
            draw_centered_text(heading_font, "지하 저장고 탈출", 800, 544, (239, 209, 158))
            draw_centered_text(
                menu_font,
                "\"나를 쫓던 것은 괴물이 아니라, 어제의 나 자신이었다.\"",
                800, 464, (242, 230, 202),
            )
            draw_centered_text(
                hint_font,
                "시간의 홀 중앙 시계에 첫 번째 보석이 밝혀졌습니다.  로비의 '기억의 일기장'을 확인해 보세요!",
                800, 396, (176, 218, 222),
            )
            draw_centered_text(
                hint_font,
                "5라운드 클리어     ·     ENTER  시간의 홀로     ·     ESC  메인 메뉴",
                800, 304, (205, 188, 163),
            )
        update_canvas()

    sounds.close()
    for font in (title_font, menu_font, heading_font, hint_font):
        font.close()
    hub.close()
    cellar.close()
    close_canvas()


if __name__ == "__main__":
    main()
