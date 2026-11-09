from pathlib import Path
from time import perf_counter

from pico2d import (
    SDL_KEYDOWN,
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
    load_image,
    open_canvas,
    update_canvas,
)


SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
TILE_SIZE = 64
MAP = (
    "###############",
    "#.............#",
    "#.............#",
    "#.............#",
    "#.....OO......#",
    "#.....OO......#",
    "#.............#",
    "#.............#",
    "#.............#",
    "###############",
)
MAP_OFFSET_X = (SCREEN_WIDTH - len(MAP[0]) * TILE_SIZE) // 2
MAP_OFFSET_Y = (SCREEN_HEIGHT - len(MAP) * TILE_SIZE) // 2
PLAYER_START = (2, 1)
WALK_ANIMATION_DURATION = 0.24
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


def is_blocked(column: int, row_from_bottom: int) -> bool:
    """Return whether a tile coordinate is outside the map or not walkable."""
    row = len(MAP) - 1 - row_from_bottom
    if not (0 <= row < len(MAP) and 0 <= column < len(MAP[row])):
        return True
    return MAP[row][column] in "#O"


def draw_tile(column: int, row: int, tile: str) -> None:
    x = MAP_OFFSET_X + column * TILE_SIZE
    y = MAP_OFFSET_Y + (len(MAP) - row - 1) * TILE_SIZE
    draw_rectangle(x, y, x + TILE_SIZE, y + TILE_SIZE, 12, 24, 42, filled=True)

    if tile == "#":
        draw_rectangle(
            x + 3, y + 2, x + TILE_SIZE - 3, y + TILE_SIZE - 3,
            7, 14, 27, filled=True,
        )
        draw_rectangle(
            x + 5, y + 8, x + TILE_SIZE - 5, y + TILE_SIZE - 8,
            48, 69, 102, filled=True,
        )
        draw_rectangle(
            x + 8, y + TILE_SIZE - 15, x + TILE_SIZE - 8, y + TILE_SIZE - 11,
            78, 100, 133, filled=True,
        )
    elif tile == "O":
        draw_rectangle(
            x + 7, y + 2, x + TILE_SIZE - 5, y + TILE_SIZE - 5,
            6, 12, 25, filled=True,
        )
        draw_rectangle(
            x + 5, y + 7, x + TILE_SIZE - 7, y + TILE_SIZE - 11,
            48, 68, 98, filled=True,
        )
        draw_rectangle(
            x + 10, y + TILE_SIZE - 18, x + TILE_SIZE - 12, y + TILE_SIZE - 14,
            72, 91, 122, filled=True,
        )
        for detail_x, detail_y in (
            (x + 13, y + 14),
            (x + TILE_SIZE - 17, y + 14),
            (x + 13, y + TILE_SIZE - 24),
            (x + TILE_SIZE - 17, y + TILE_SIZE - 24),
        ):
            draw_rectangle(
                detail_x, detail_y, detail_x + 4, detail_y + 4,
                24, 37, 58, filled=True,
            )
    else:
        draw_rectangle(
            x, y, x + TILE_SIZE, y + TILE_SIZE,
            25, 43, 66, filled=False,
        )


def draw_map() -> None:
    clear_canvas()
    for row_index, row in enumerate(MAP):
        for column_index, tile in enumerate(row):
            draw_tile(column_index, row_index, tile)


def main() -> None:
    open_canvas(SCREEN_WIDTH, SCREEN_HEIGHT)
    sprite = load_image(
        str(Path(__file__).resolve().parents[1] / "assets" / "player_sprite.png")
    )
    player_column, player_row = PLAYER_START
    facing = "down"
    animation_time = 0.0
    walking_time = 0.0
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
                    move_x, move_y = KEY_DIRECTIONS[event.key]
                    facing = (
                        "right" if move_x > 0 else
                        "left" if move_x < 0 else
                        "up" if move_y > 0 else
                        "down"
                    )
                    next_column = player_column + move_x
                    next_row = player_row + move_y
                    if not is_blocked(next_column, next_row):
                        player_column = next_column
                        player_row = next_row
                        walking_time = WALK_ANIMATION_DURATION

        if walking_time > 0:
            animation_time += delta_time
            walking_time = max(0.0, walking_time - delta_time)

        draw_map()
        frame = int(animation_time * 12) % 4 if walking_time > 0 else 0
        sprite.clip_draw(
            frame * SPRITE_FRAME_SIZE,
            SPRITE_ROWS[facing],
            SPRITE_FRAME_SIZE,
            SPRITE_FRAME_SIZE,
            MAP_OFFSET_X + (player_column + 0.5) * TILE_SIZE,
            MAP_OFFSET_Y + (player_row + 0.5) * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE,
        )
        update_canvas()

    close_canvas()


if __name__ == "__main__":
    main()
