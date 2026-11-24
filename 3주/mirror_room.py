"""2번째 미니게임: 'Ⅱ. 거울의 회랑' — 거울 속의 나와 동시 조종 퍼즐."""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sin
from typing import Callable

import pico2d
from pico2d import Image, draw_circle, draw_line, draw_rectangle


SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900

GRID_COLS = 10
GRID_ROWS = 9
TILE_SIZE = 72
DIVIDER_HALF_WIDTH = 18
LEFT_ORIGIN_X = SCREEN_WIDTH // 2 - DIVIDER_HALF_WIDTH - GRID_COLS * TILE_SIZE   # 62
RIGHT_ORIGIN_X = SCREEN_WIDTH // 2 + DIVIDER_HALF_WIDTH                           # 818
BOARD_ORIGIN_Y = 126                                                              # 126..774

STEP_DURATION = 0.13
SPRITE_FRAME_SIZE = 320
SPRITE_ROWS = {
    "down": 3 * SPRITE_FRAME_SIZE,
    "left": 2 * SPRITE_FRAME_SIZE,
    "right": SPRITE_FRAME_SIZE,
    "up": 0,
}


@dataclass(frozen=True)
class MirrorStage:
    title: str
    subtitle: str
    left_map: tuple[str, ...]
    right_map: tuple[str, ...]


# 1단계: 비대칭 기둥에 한쪽을 걸어 위치를 맞춘 뒤, 두 출구(G)에 동시에 도달하는 입문 스테이지
MIRROR_STAGES: tuple[MirrorStage, ...] = (
    MirrorStage(
        title="1단계 · 거울과 눈 맞추기",
        subtitle="좌우 반전으로 움직입니다. 기둥에 한쪽을 걸어 위치를 맞춘 뒤 동시에 출구(G)에 서세요!",
        left_map=(
            "##########",
            "#.......G#",
            "#..#.....#",
            "#..#..#..#",
            "#.....#..#",
            "#..#.....#",
            "#........#",
            "#P....#..#",
            "##########",
        ),
        right_map=(
            "##########",
            "#G.......#",
            "#.....#..#",
            "#........#",
            "#..#..#..#",
            "#..#.....#",
            "#.....#..#",
            "#.....#.P#",
            "##########",
        ),
    ),
)


def _fill(x: float, y: float, width: float, height: float, color: tuple[int, ...]) -> None:
    draw_rectangle(
        int(x), int(y), int(x + width) - 1, int(y + height) - 1, *color, filled=True
    )


def _find_tile(tile_map: tuple[str, ...], target: str) -> tuple[int, int]:
    for row, line in enumerate(tile_map):
        for col, ch in enumerate(line):
            if ch == target:
                return col, row
    raise ValueError(f"Tile '{target}' not found in mirror stage map")


def _cell_center(origin_x: int, col: float, row: float) -> tuple[float, float]:
    x = origin_x + (col + 0.5) * TILE_SIZE
    y = BOARD_ORIGIN_Y + (GRID_ROWS - 1 - row + 0.5) * TILE_SIZE
    return x, y


def _facing_from_delta(dx: int, dy: int, fallback: str) -> str:
    if dx > 0:
        return "right"
    if dx < 0:
        return "left"
    if dy < 0:
        return "up"
    if dy > 0:
        return "down"
    return fallback


class MirrorHallRun:
    """Manage grid-interpolated mirror-twin puzzle state for 'Ⅱ. 거울의 회랑'."""

    def __init__(self) -> None:
        self.stage_index = 0
        self.elapsed = 0.0
        self.moves = 0
        self.events: list[tuple[str, float, float]] = []
        self.notice = ""
        self.notice_until = 0.0
        self.reset_all()

    @property
    def stage(self) -> MirrorStage:
        return MIRROR_STAGES[self.stage_index]

    @property
    def stage_count(self) -> int:
        return len(MIRROR_STAGES)

    def reset_all(self) -> None:
        self.stage_index = 0
        self.elapsed = 0.0
        self.begin_stage()

    def begin_stage(self, notice: str | None = None) -> None:
        st = self.stage
        self.left_pos = _find_tile(st.left_map, "P")
        self.right_pos = _find_tile(st.right_map, "P")
        self.left_goal = _find_tile(st.left_map, "G")
        self.right_goal = _find_tile(st.right_map, "G")
        self.left_prev = self.left_pos
        self.right_prev = self.right_pos
        self.left_facing = "up"
        self.right_facing = "up"
        self.step_timer = STEP_DURATION
        self.moves = 0
        self.step_frame_toggle = 0
        self.notice = st.subtitle if notice is None else notice
        self.notice_until = self.elapsed + 5.0

    def is_stepping(self) -> bool:
        return self.step_timer < STEP_DURATION

    def _can_walk(self, tile_map: tuple[str, ...], col: int, row: int) -> bool:
        if not (0 <= row < GRID_ROWS and 0 <= col < GRID_COLS):
            return False
        return tile_map[row][col] != "#"

    def try_step(self, dx: int, dy: int) -> str:
        """Attempt one synchronized grid step. Horizontal input is mirrored on the right."""
        if (dx == 0 and dy == 0) or self.is_stepping():
            return "playing"
        # 수직(위/아래)은 화면 좌표(up=+1)를 행 좌표(up=-1)로 변환한다.
        row_delta = -dy
        left_dx, right_dx = dx, -dx

        self.left_facing = _facing_from_delta(left_dx, row_delta, self.left_facing)
        self.right_facing = _facing_from_delta(right_dx, row_delta, self.right_facing)

        nlx, nly = self.left_pos[0] + left_dx, self.left_pos[1] + row_delta
        nrx, nry = self.right_pos[0] + right_dx, self.right_pos[1] + row_delta

        left_ok = self._can_walk(self.stage.left_map, nlx, nly)
        right_ok = self._can_walk(self.stage.right_map, nrx, nry)

        if not left_ok and not right_ok:
            return "blocked"

        self.left_prev = self.left_pos
        self.right_prev = self.right_pos
        if left_ok:
            self.left_pos = (nlx, nly)
        if right_ok:
            self.right_pos = (nrx, nry)

        self.step_timer = 0.0
        self.moves += 1
        self.step_frame_toggle = (self.step_frame_toggle + 1) % 2
        lx, ly = _cell_center(LEFT_ORIGIN_X, *self.left_pos)
        self.events.append(("step", lx, ly))

        if self.left_pos == self.left_goal and self.right_pos == self.right_goal:
            return self._complete_stage()
        return "playing"

    def _complete_stage(self) -> str:
        lx, ly = _cell_center(LEFT_ORIGIN_X, *self.left_goal)
        rx, ry = _cell_center(RIGHT_ORIGIN_X, *self.right_goal)
        if self.stage_index + 1 >= len(MIRROR_STAGES):
            self.events.append(("clear", (lx + rx) / 2, (ly + ry) / 2))
            return "clear"
        self.events.append(("next", lx, ly))
        self.events.append(("next", rx, ry))
        self.stage_index += 1
        self.begin_stage()
        return "next"

    def update(self, held_dx: int, held_dy: int, delta_time: float) -> str:
        self.events.clear()
        if delta_time <= 0.0:
            return "playing"
        self.elapsed += delta_time
        if self.step_timer < STEP_DURATION:
            self.step_timer = min(STEP_DURATION, self.step_timer + delta_time)
            return "playing"

        if held_dx or held_dy:
            # 대각선 동시 입력 시 수평/수직 중 한 축으로 깔끔하게 칸 이동한다.
            step_dx = held_dx if held_dx != 0 else 0
            step_dy = 0 if step_dx != 0 else held_dy
            return self.try_step(step_dx, step_dy)
        return "playing"

    def visual_positions(self) -> tuple[tuple[float, float], tuple[float, float]]:
        t = min(1.0, self.step_timer / STEP_DURATION)
        # 부드러운 ease-out 보간
        eased = 1.0 - (1.0 - t) ** 2
        lc = self.left_prev[0] + (self.left_pos[0] - self.left_prev[0]) * eased
        lr = self.left_prev[1] + (self.left_pos[1] - self.left_prev[1]) * eased
        rc = self.right_prev[0] + (self.right_pos[0] - self.right_prev[0]) * eased
        rr = self.right_prev[1] + (self.right_pos[1] - self.right_prev[1]) * eased
        return _cell_center(LEFT_ORIGIN_X, lc, lr), _cell_center(RIGHT_ORIGIN_X, rc, rr)

    def walk_frame(self) -> int:
        if not self.is_stepping():
            return 0
        return 1 if self.step_frame_toggle == 0 else 3


def _draw_board(
    tile_map: tuple[str, ...],
    origin_x: int,
    mirrored: bool,
    elapsed: float,
    on_goal: bool,
) -> None:
    pulse = 0.5 + 0.5 * sin(elapsed * 3.6)

    # 외곽 석조 프레임
    board_w = GRID_COLS * TILE_SIZE
    board_h = GRID_ROWS * TILE_SIZE
    frame_color = (146, 126, 186) if mirrored else (168, 138, 92)
    _fill(origin_x - 6, BOARD_ORIGIN_Y - 6, board_w + 12, board_h + 12, (20, 22, 32))
    draw_rectangle(
        origin_x - 6, BOARD_ORIGIN_Y - 6,
        origin_x + board_w + 6, BOARD_ORIGIN_Y + board_h + 6,
        *frame_color, filled=False,
    )

    for row, line in enumerate(tile_map):
        for col, ch in enumerate(line):
            tx = origin_x + col * TILE_SIZE
            ty = BOARD_ORIGIN_Y + (GRID_ROWS - 1 - row) * TILE_SIZE
            checker = (col + row) % 2

            if ch == "#":
                if mirrored:
                    base = (48, 44, 68)
                    top_trim = (118, 108, 152)
                    brick = (64, 58, 88)
                else:
                    base = (58, 54, 58)
                    top_trim = (132, 118, 104)
                    brick = (78, 72, 74)
                _fill(tx, ty, TILE_SIZE, TILE_SIZE, (24, 24, 32))
                _fill(tx + 2, ty + 6, TILE_SIZE - 4, TILE_SIZE - 8, base)
                _fill(tx + 6, ty + 14, TILE_SIZE - 12, TILE_SIZE - 24, brick)
                _fill(tx + 2, ty + TILE_SIZE - 7, TILE_SIZE - 4, 5, top_trim)
                draw_rectangle(tx + 2, ty + 6, tx + TILE_SIZE - 3, ty + TILE_SIZE - 3, 34, 34, 44)
                continue

            # 바닥 석재 타일 (현실: 따뜻한 석재 / 거울: 차가운 은보라 석재)
            if mirrored:
                floor_col = (44, 42, 66) if checker == 0 else (38, 36, 58)
                hi_col = (58, 56, 86)
            else:
                floor_col = (54, 50, 56) if checker == 0 else (47, 44, 50)
                hi_col = (70, 64, 68)
            _fill(tx + 1, ty + 1, TILE_SIZE - 2, TILE_SIZE - 2, floor_col)
            _fill(tx + 2, ty + TILE_SIZE - 3, TILE_SIZE - 4, 2, hi_col)
            draw_rectangle(tx + 5, ty + 5, tx + TILE_SIZE - 6, ty + TILE_SIZE - 6,
                           floor_col[0] - 6, floor_col[1] - 6, floor_col[2] - 5)

            if ch == "G":
                cx, cy = tx + TILE_SIZE / 2, ty + TILE_SIZE / 2
                glow_col = (128, 236, 206) if on_goal else (
                    (202, 152, 248) if mirrored else (242, 198, 108)
                )
                _fill(tx + 10, ty + 10, TILE_SIZE - 20, TILE_SIZE - 20, (24, 26, 38))
                draw_rectangle(tx + 10, ty + 10, tx + TILE_SIZE - 10, ty + TILE_SIZE - 10, *glow_col)
                draw_circle(cx, cy, int(18 + 4 * pulse), *glow_col, int(52 + 34 * pulse), filled=True)
                draw_circle(cx, cy, 22, *glow_col, 210)
                # 마름모 출구 문양
                draw_line(cx - 12, cy, cx, cy + 12, *glow_col)
                draw_line(cx, cy + 12, cx + 12, cy, *glow_col)
                draw_line(cx + 12, cy, cx, cy - 12, *glow_col)
                draw_line(cx, cy - 12, cx - 12, cy, *glow_col)


def _draw_center_mirror_divider(elapsed: float) -> None:
    cx = SCREEN_WIDTH // 2
    left = cx - DIVIDER_HALF_WIDTH
    width = DIVIDER_HALF_WIDTH * 2
    bottom = BOARD_ORIGIN_Y - 10
    height = GRID_ROWS * TILE_SIZE + 20

    # 은빛 거울 유리 프레임
    _fill(left, bottom, width, height, (34, 38, 56))
    _fill(left + 5, bottom + 6, width - 10, height - 12, (76, 92, 128))
    _fill(left + 10, bottom + 8, width - 20, height - 16, (134, 166, 206))
    draw_rectangle(left, bottom, left + width, bottom + height, 192, 174, 134)

    # 거울 표면을 타고 흐르는 반짝임 빛줄기
    for band in range(4):
        shift = (elapsed * 55 + band * 170) % (height - 40)
        by = bottom + 16 + shift
        alpha = int(110 * sin(pi * shift / (height - 40)))
        draw_line(left + 6, by, left + width - 6, by + 18, 228, 242, 255, max(12, alpha))

    # 상단·하단 황동 거울 장식
    for cap_y in (bottom, bottom + height - 14):
        _fill(left - 6, cap_y, width + 12, 14, (176, 144, 88))
        draw_rectangle(left - 6, cap_y, left + width + 6, cap_y + 14, 228, 196, 132)


def draw_mirror_hall(
    menu_font,
    hint_font,
    draw_centered_text: Callable,
    sprite: Image,
    run: MirrorHallRun,
) -> None:
    # 깊은 밤빛 배경
    _fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (14, 16, 26))
    _fill(0, BOARD_ORIGIN_Y - 30, SCREEN_WIDTH // 2, GRID_ROWS * TILE_SIZE + 60, (22, 19, 24))
    _fill(SCREEN_WIDTH // 2, BOARD_ORIGIN_Y - 30, SCREEN_WIDTH // 2, GRID_ROWS * TILE_SIZE + 60, (18, 18, 32))

    left_on_goal = run.left_pos == run.left_goal
    right_on_goal = run.right_pos == run.right_goal

    _draw_board(run.stage.left_map, LEFT_ORIGIN_X, False, run.elapsed, left_on_goal)
    _draw_board(run.stage.right_map, RIGHT_ORIGIN_X, True, run.elapsed, right_on_goal)
    _draw_center_mirror_divider(run.elapsed)

    # 방 소제목
    left_mid_x = LEFT_ORIGIN_X + GRID_COLS * TILE_SIZE / 2
    right_mid_x = RIGHT_ORIGIN_X + GRID_COLS * TILE_SIZE / 2
    draw_centered_text(hint_font, "현실의 회랑", left_mid_x, 804, (238, 208, 152))
    draw_centered_text(hint_font, "거울 속 회랑  (좌우 반전)", right_mid_x, 804, (198, 164, 242))

    # 두 캐릭터 렌더링
    (lx, ly), (rx, ry) = run.visual_positions()
    frame = run.walk_frame()
    char_size = TILE_SIZE * 1.05

    # 왼쪽: 실제 주인공
    draw_circle(lx, ly - 14, 14, 10, 10, 14, 145, filled=True)
    sprite.clip_draw(
        frame * SPRITE_FRAME_SIZE, SPRITE_ROWS[run.left_facing],
        SPRITE_FRAME_SIZE, SPRITE_FRAME_SIZE, lx, ly + 4, char_size, char_size,
    )

    # 오른쪽: 거울 속의 나 (은빛-보라 반투명 반사체)
    draw_circle(rx, ry - 14, 14, 16, 12, 26, 140, filled=True)
    draw_circle(rx, ry, 24, 196, 154, 250, 125)
    pico2d.SDL_SetTextureColorMod(sprite.texture, 208, 168, 255)
    sprite.opacify(0.76)
    sprite.clip_draw(
        frame * SPRITE_FRAME_SIZE, SPRITE_ROWS[run.right_facing],
        SPRITE_FRAME_SIZE, SPRITE_FRAME_SIZE, rx, ry + 4, char_size, char_size,
    )
    sprite.opacify(1.0)
    pico2d.SDL_SetTextureColorMod(sprite.texture, 255, 255, 255)

    # 상단 HUD 바
    _fill(18, 844, 1564, 46, (20, 20, 30, 238))
    draw_rectangle(18, 844, 1582, 890, 156, 134, 188, filled=False)
    menu_font.draw(36, 867, "Ⅱ. 거울의 회랑", (222, 196, 248))
    hint_font.draw(318, 866, f"{run.stage.title}  ({run.stage_index + 1}/{run.stage_count})", (236, 224, 198))
    hint_font.draw(760, 866, f"이동 횟수  {run.moves}", (182, 208, 220))
    status_text = (
        "양쪽 정렬 완료!" if (left_on_goal and right_on_goal)
        else ("현실 출구 도달 · 거울을 맞추세요" if left_on_goal
              else ("거울 출구 도달 · 현실을 맞추세요" if right_on_goal else "두 출구에 동시에 서세요"))
    )
    status_col = (128, 236, 204) if (left_on_goal or right_on_goal) else (196, 186, 210)
    hint_font.draw(975, 866, status_text, status_col)
    draw_centered_text(hint_font, "R 재시작  ·  ESC 일시정지", 1458, 866, (164, 186, 196))

    # 하단 안내 / 공지 바
    if run.notice and run.elapsed < run.notice_until:
        _fill(260, 62, 1080, 40, (18, 20, 32, 232))
        draw_rectangle(260, 62, 1340, 102, 158, 136, 188, filled=False)
        draw_centered_text(hint_font, run.notice, SCREEN_WIDTH / 2, 82, (238, 224, 196))

    _fill(440, 14, 720, 34, (18, 20, 30, 220))
    draw_rectangle(440, 14, 1160, 48, 82, 92, 114, filled=False)
    draw_centered_text(
        hint_font,
        "방향키 / WASD 한 칸 이동 (좌우 반전)   ·   R 다시 시작   ·   ESC 일시정지",
        SCREEN_WIDTH / 2, 31, (176, 190, 202),
    )
