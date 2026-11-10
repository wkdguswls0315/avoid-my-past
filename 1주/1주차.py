import ctypes
from os import environ
from pathlib import Path
from time import perf_counter

import pico2d
from pico2d import (
    Font,
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
    Mix_Volume,
    Mix_VolumeMusic,
    close_canvas,
    clear_canvas,
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
MAP = (
    "#########################",
    "#.......................#",
    "#.....OOOO..............#",
    "#.......................#",
    "#.......................#",
    "#............O..........#",
    "#............O..........#",
    "#............O..........#",
    "#.......................#",
    "#.................OOOO..#",
    "#.......................#",
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
PLAYER_START = (
    (START_TILE[0] + 0.5) * TILE_WIDTH,
    (len(MAP) - START_TILE[1] - 0.5) * TILE_HEIGHT,
)
PLAYER_RADIUS = 13
PLAYER_SPEED = 240
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
            if MAP[row][column] in "#O":
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


def tile_origin(column: int, row: int) -> tuple[float, float]:
    return (
        MAP_OFFSET_X + column * TILE_WIDTH,
        MAP_OFFSET_Y + (len(MAP) - row - 1) * TILE_HEIGHT,
    )


def draw_tile(column: int, row: int, tile: str) -> None:
    x, y = tile_origin(column, row)
    draw_rectangle(x, y, x + TILE_WIDTH, y + TILE_HEIGHT, 12, 24, 42, filled=True)

    if tile == "#":
        draw_rectangle(
            x + 3, y + 2, x + TILE_WIDTH - 3, y + TILE_HEIGHT - 3,
            7, 14, 27, filled=True,
        )
        draw_rectangle(
            x + 5, y + 8, x + TILE_WIDTH - 5, y + TILE_HEIGHT - 8,
            48, 69, 102, filled=True,
        )
        draw_rectangle(
            x + 8, y + TILE_HEIGHT - 15, x + TILE_WIDTH - 8, y + TILE_HEIGHT - 11,
            78, 100, 133, filled=True,
        )
    elif tile == "O":
        draw_rectangle(
            x + 7, y + 2, x + TILE_WIDTH - 5, y + TILE_HEIGHT - 5,
            6, 12, 25, filled=True,
        )
        draw_rectangle(
            x + 5, y + 7, x + TILE_WIDTH - 7, y + TILE_HEIGHT - 11,
            48, 68, 98, filled=True,
        )
        draw_rectangle(
            x + 10, y + TILE_HEIGHT - 18, x + TILE_WIDTH - 12, y + TILE_HEIGHT - 14,
            72, 91, 122, filled=True,
        )
        for detail_x, detail_y in (
            (x + 13, y + 14),
            (x + TILE_WIDTH - 17, y + 14),
            (x + 13, y + TILE_HEIGHT - 24),
            (x + TILE_WIDTH - 17, y + TILE_HEIGHT - 24),
        ):
            draw_rectangle(
                detail_x, detail_y, detail_x + 4, detail_y + 4,
                24, 37, 58, filled=True,
            )
    else:
        draw_rectangle(
            x, y, x + TILE_WIDTH, y + TILE_HEIGHT,
            25, 43, 66, filled=False,
        )


def draw_start_pad() -> None:
    center_x, center_y = PLAYER_START
    draw_rectangle(
        center_x - 24, center_y - 27, center_x + 24, center_y + 27,
        34, 52, 68, filled=True,
    )
    draw_rectangle(
        center_x - 24, center_y - 27, center_x + 24, center_y + 27,
        75, 151, 151, filled=False,
    )


def draw_goal_door() -> None:
    x, y = tile_origin(*GOAL_TILE)
    draw_rectangle(
        x + 8, y + 4, x + TILE_WIDTH - 8, y + TILE_HEIGHT - 3,
        51, 29, 18, filled=True,
    )
    draw_rectangle(
        x + 12, y + 7, x + TILE_WIDTH - 12, y + TILE_HEIGHT - 3,
        139, 82, 39, filled=True,
    )
    draw_rectangle(
        x + 17, y + 12, x + TILE_WIDTH - 17, y + TILE_HEIGHT - 3,
        105, 56, 29, filled=True,
    )
    draw_rectangle(
        x + TILE_WIDTH / 2 - 2, y + 12,
        x + TILE_WIDTH / 2 + 2, y + TILE_HEIGHT - 3,
        161, 98, 47, filled=True,
    )
    draw_rectangle(
        x + 13, y + 8, x + TILE_WIDTH - 13, y + 12,
        161, 98, 47, filled=True,
    )
    draw_rectangle(
        x + TILE_WIDTH - 22, y + 29,
        x + TILE_WIDTH - 18, y + 33,
        238, 190, 83, filled=True,
    )


def draw_map() -> None:
    clear_canvas()
    for row_index, row in enumerate(MAP):
        for column_index, tile in enumerate(row):
            draw_tile(column_index, row_index, tile)
    draw_start_pad()
    draw_goal_door()


def sdl_error_message() -> str:
    error = pico2d.SDL_GetError()
    if isinstance(error, bytes):
        return error.decode("utf-8", errors="replace")
    return str(error)


def set_display_mode(fullscreen: bool) -> None:
    window = pico2d.window
    flags = pico2d.SDL_WINDOW_FULLSCREEN_DESKTOP if fullscreen else 0
    if pico2d.SDL_SetWindowFullscreen(window, flags) != 0:
        raise RuntimeError(f"Could not change display mode: {sdl_error_message()}")

    if not fullscreen:
        pico2d.SDL_SetWindowSize(window, WINDOW_WIDTH, WINDOW_HEIGHT)
        pico2d.SDL_SetWindowPosition(
            window, pico2d.SDL_WINDOWPOS_CENTERED, pico2d.SDL_WINDOWPOS_CENTERED
        )

    if pico2d.SDL_RenderSetLogicalSize(
        pico2d.renderer, SCREEN_WIDTH, SCREEN_HEIGHT
    ) != 0:
        raise RuntimeError(f"Could not scale the game canvas: {sdl_error_message()}")


def set_sound_enabled(enabled: bool) -> None:
    if pico2d.audio_on:
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
    font: Font, label: str, y: float, selected: bool
) -> None:
    left, right = 540, 1060
    bottom, top = y - 26, y + 34
    if selected:
        draw_rectangle(left, bottom, right, top, 34, 52, 68, filled=True)
    draw_rectangle(left, bottom, right, top, 75, 151, 151, filled=False)
    color = (245, 231, 199) if selected else (164, 182, 199)
    draw_centered_text(font, label, SCREEN_WIDTH / 2, y - 10, color)


def draw_menu(
    title_font: Font, menu_font: Font, selected_item: int
) -> None:
    clear_canvas()
    draw_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 12, 24, 42, filled=True)
    draw_centered_text(
        title_font, "Avoid My Past", SCREEN_WIDTH / 2, 742, (231, 220, 191)
    )
    draw_rectangle(620, 713, 980, 716, 75, 151, 151, filled=True)
    for index, (label, y) in enumerate(
        (("게임 시작", 500), ("종료", 380), ("설정", 260))
    ):
        draw_menu_button(menu_font, label, y, index == selected_item)
    draw_centered_text(
        menu_font, "방향키로 선택하고 Enter로 확인", SCREEN_WIDTH / 2, 145,
        (127, 149, 169),
    )


def draw_settings(
    title_font: Font,
    menu_font: Font,
    selected_item: int,
    sound_enabled: bool,
    fullscreen: bool,
) -> None:
    clear_canvas()
    draw_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 12, 24, 42, filled=True)
    draw_centered_text(
        title_font, "설정", SCREEN_WIDTH / 2, 710, (231, 220, 191)
    )
    options = (
        f"소리: {'켜짐' if sound_enabled else '꺼짐'}",
        f"화면 모드: {'전체화면' if fullscreen else '창화면 (1280 x 720)'}",
        "돌아가기",
    )
    for index, (label, y) in enumerate(zip(options, (510, 390, 270))):
        draw_menu_button(menu_font, label, y, index == selected_item)
    draw_centered_text(
        menu_font, "방향키로 선택하고 Enter로 변경", SCREEN_WIDTH / 2, 145,
        (127, 149, 169),
    )


def main() -> None:
    open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT)
    set_display_mode(fullscreen=False)
    title_font = load_font(
        str(Path(environ["WINDIR"]) / "Fonts" / "malgun.ttf"), 56
    )
    menu_font = load_font(
        str(Path(environ["WINDIR"]) / "Fonts" / "malgun.ttf"), 30
    )
    sprite = load_image(
        str(Path(__file__).resolve().parents[1] / "assets" / "player_sprite.png")
    )
    player_x, player_y = PLAYER_START
    facing = "down"
    animation_time = 0.0
    held_keys: set[int] = set()
    previous_time = perf_counter()
    running = True
    screen = "menu"
    selected_menu_item = 0
    selected_settings_item = 0
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
                        screen = "menu"
                    elif screen == "game":
                        screen = "menu"
                        held_keys.clear()
                    else:
                        running = False
                elif screen == "game" and event.key in KEY_DIRECTIONS:
                    held_keys.add(event.key)
                elif screen == "menu" and event.key in (SDLK_UP, SDLK_w):
                    selected_menu_item = (selected_menu_item - 1) % 3
                elif screen == "menu" and event.key in (SDLK_DOWN, SDLK_s):
                    selected_menu_item = (selected_menu_item + 1) % 3
                elif screen == "settings" and event.key in (SDLK_UP, SDLK_w):
                    selected_settings_item = (selected_settings_item - 1) % 3
                elif screen == "settings" and event.key in (SDLK_DOWN, SDLK_s):
                    selected_settings_item = (selected_settings_item + 1) % 3
                elif screen == "menu" and event.key in (SDLK_RETURN, SDLK_KP_ENTER):
                    if selected_menu_item == 0:
                        screen = "game"
                        player_x, player_y = PLAYER_START
                        animation_time = 0.0
                        held_keys.clear()
                    elif selected_menu_item == 1:
                        running = False
                    else:
                        screen = "settings"
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
                        screen = "menu"
            elif event.type == SDL_KEYUP and event.key in KEY_DIRECTIONS:
                held_keys.discard(event.key)

        if screen == "game":
            move_x = sum(KEY_DIRECTIONS[key][0] for key in held_keys)
            move_y = sum(KEY_DIRECTIONS[key][1] for key in held_keys)
            is_moving = move_x != 0 or move_y != 0

            if is_moving:
                player_x, player_y = move_player(
                    player_x, player_y, move_x, move_y, delta_time
                )
                if abs(move_x) > abs(move_y):
                    facing = "right" if move_x > 0 else "left"
                else:
                    facing = "up" if move_y > 0 else "down"
                animation_time += delta_time

            draw_map()
            frame = int(animation_time * 8) % 4 if is_moving else 0
            sprite.clip_draw(
                frame * SPRITE_FRAME_SIZE,
                SPRITE_ROWS[facing],
                SPRITE_FRAME_SIZE,
                SPRITE_FRAME_SIZE,
                player_x,
                player_y,
                TILE_WIDTH,
                TILE_HEIGHT,
            )
        elif screen == "settings":
            draw_settings(
                title_font, menu_font, selected_settings_item,
                sound_enabled, fullscreen,
            )
        else:
            draw_menu(title_font, menu_font, selected_menu_item)
        update_canvas()

    close_canvas()


if __name__ == "__main__":
    main()
