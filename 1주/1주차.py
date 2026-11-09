from os import environ
from pathlib import Path
from time import perf_counter

from pico2d import (
    Font,
    SDL_KEYDOWN,
    SDL_KEYUP,
    SDL_QUIT,
    SDLK_DOWN,
    SDLK_ESCAPE,
    SDLK_LEFT,
    SDLK_RIGHT,
    SDLK_UP,
    SDLK_a,
    SDLK_d,
    SDLK_s,
    SDLK_w,
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
MAP = (
    "#########################",
    "#...................OO..#",
    "#...................OO..#",
    "#.......OO......OO......#",
    "#.......OO......OO......#",
    "#...................OO..#",
    "#...................OO..#",
    "#...........OO..OO......#",
    "#...OO......OO..OO......#",
    "#...OO..............OO..#",
    "#.......OO..........OO..#",
    "#.......OO......OO......#",
    "#...............OO......#",
    "#########################",
)
TILE_WIDTH = SCREEN_WIDTH / len(MAP[0])
TILE_HEIGHT = SCREEN_HEIGHT / len(MAP)
MAP_OFFSET_X = 0
MAP_OFFSET_Y = 0
START_TILE = (2, 12)
START_SIGN_TILE = (3, 12)
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


def draw_start_sign(font: Font) -> None:
    x, y = tile_origin(*START_SIGN_TILE)
    center_x = x + TILE_WIDTH / 2
    draw_rectangle(
        center_x - 3, y + 5, center_x + 3, y + 29,
        91, 58, 31, filled=True,
    )
    draw_rectangle(
        center_x - 27, y + 27, center_x + 27, y + 50,
        72, 43, 24, filled=True,
    )
    draw_rectangle(
        center_x - 24, y + 30, center_x + 24, y + 47,
        177, 127, 66, filled=True,
    )
    font.draw(center_x - 12, y + 32, "출발", (255, 239, 190))


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


def draw_map(start_sign_font: Font) -> None:
    clear_canvas()
    for row_index, row in enumerate(MAP):
        for column_index, tile in enumerate(row):
            draw_tile(column_index, row_index, tile)
    draw_start_sign(start_sign_font)
    draw_goal_door()


def main() -> None:
    open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT)
    start_sign_font = load_font(
        str(Path(environ["WINDIR"]) / "Fonts" / "malgun.ttf"), 12
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

    while running:
        current_time = perf_counter()
        delta_time = min(current_time - previous_time, 0.05)
        previous_time = current_time

        for event in get_events():
            if event.type == SDL_QUIT:
                running = False
            elif event.type == SDL_KEYDOWN:
                if event.key == SDLK_ESCAPE:
                    running = False
                elif event.key in KEY_DIRECTIONS:
                    held_keys.add(event.key)
            elif event.type == SDL_KEYUP and event.key in KEY_DIRECTIONS:
                held_keys.discard(event.key)

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

        draw_map(start_sign_font)
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
        update_canvas()

    close_canvas()


if __name__ == "__main__":
    main()
