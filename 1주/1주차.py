import ctypes
from os import environ
from pathlib import Path
from time import perf_counter

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


def mouse_event_to_canvas_position(x: int, y: int) -> tuple[float, float]:
    """Convert Pico2D logical mouse-event coordinates to the canvas origin."""
    return float(x), SCREEN_HEIGHT - y


def menu_item_at(screen: str, x: float, y: float) -> int | None:
    item_positions = (
        tuple(item_y for _, item_y in MENU_ITEMS)
        if screen == "menu"
        else SETTINGS_ITEM_Y
    )
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
) -> None:
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


def main() -> None:
    open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT)
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
            elif event.type == SDL_MOUSEMOTION and screen in ("menu", "settings"):
                mouse_x, mouse_y = mouse_event_to_canvas_position(event.x, event.y)
                hovered_item = menu_item_at(screen, mouse_x, mouse_y)
                if hovered_item is not None:
                    if screen == "menu":
                        selected_menu_item = hovered_item
                    else:
                        selected_settings_item = hovered_item
            elif (
                event.type == SDL_MOUSEBUTTONDOWN
                and event.button == SDL_BUTTON_LEFT
                and screen in ("menu", "settings")
            ):
                mouse_x, mouse_y = mouse_event_to_canvas_position(event.x, event.y)
                clicked_item = menu_item_at(screen, mouse_x, mouse_y)
                if clicked_item is not None and screen == "menu":
                    selected_menu_item = clicked_item
                    if clicked_item == 0:
                        screen = "game"
                        player_x, player_y = PLAYER_START
                        animation_time = 0.0
                        held_keys.clear()
                    elif clicked_item == 1:
                        running = False
                    else:
                        screen = "settings"
                elif clicked_item is not None:
                    selected_settings_item = clicked_item
                    if clicked_item == 0:
                        sound_enabled = not sound_enabled
                        set_sound_enabled(sound_enabled)
                    elif clicked_item == 1:
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
                heading_font, menu_font, hint_font, selected_settings_item,
                sound_enabled, fullscreen, sprite,
            )
        else:
            draw_menu(
                title_font, menu_font, hint_font, selected_menu_item, sprite
            )
        update_canvas()

    close_canvas()


if __name__ == "__main__":
    main()
