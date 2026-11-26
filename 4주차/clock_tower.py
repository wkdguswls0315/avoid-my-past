"""3번째 미니게임: 'Ⅲ. 멈춘 시계탑' — 원형 시계판 아레나 & 시간 정지 액션."""

from __future__ import annotations

from math import cos, hypot, pi, sin
from typing import Callable

from pico2d import Image, draw_circle, draw_line, draw_rectangle


SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900

ARENA_CX = SCREEN_WIDTH / 2.0
ARENA_CY = 442.0
ARENA_RADIUS = 362.0
CORE_RADIUS = 46.0

PLAYER_RADIUS = 16.0
PLAYER_SPEED = 240.0
PLAYER_ACCEL = 960.0
PLAYER_STOP_ACCEL = 1280.0

SPRITE_FRAME_SIZE = 320
SPRITE_ROWS = {
    "down": 3 * SPRITE_FRAME_SIZE,
    "left": 2 * SPRITE_FRAME_SIZE,
    "right": SPRITE_FRAME_SIZE,
    "up": 0,
}


def _fill(x: float, y: float, width: float, height: float, color: tuple[int, ...]) -> None:
    draw_rectangle(
        int(x), int(y), int(x + width) - 1, int(y + height) - 1, *color, filled=True
    )


def _approach(current: float, target: float, delta: float) -> float:
    if current < target:
        return min(target, current + delta)
    return max(target, current - delta)


class ClockTowerRun:
    """Manage circular clock-arena player movement and round state for 'Ⅲ. 멈춘 시계탑'."""

    def __init__(self) -> None:
        self.elapsed = 0.0
        self.events: list[tuple[str, float, float]] = []
        self.notice = ""
        self.notice_until = 0.0
        self.reset_all()

    def reset_all(self) -> None:
        self.elapsed = 0.0
        self.begin_round("거대한 시계탑 내부에 들어섰습니다. 방향키/WASD로 시계판을 이동해 보세요.")

    def begin_round(self, notice: str = "") -> None:
        self.x = ARENA_CX
        self.y = ARENA_CY - 220.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing = "up"
        self.frame = 0
        self.animation_time = 0.0
        self.last_step_frame = 0
        self.notice = notice
        self.notice_until = self.elapsed + 4.5

    def update(self, move_x: int, move_y: int, delta_time: float) -> str:
        self.events.clear()
        if delta_time <= 0.0:
            return "playing"
        self.elapsed += delta_time

        input_len = hypot(move_x, move_y)
        if input_len:
            target_vx = move_x / input_len * PLAYER_SPEED
            target_vy = move_y / input_len * PLAYER_SPEED
        else:
            target_vx = target_vy = 0.0

        accel = PLAYER_ACCEL if input_len else PLAYER_STOP_ACCEL
        self.vx = _approach(self.vx, target_vx, accel * delta_time)
        self.vy = _approach(self.vy, target_vy, accel * delta_time)

        prev_x, prev_y = self.x, self.y
        nx = self.x + self.vx * delta_time
        ny = self.y + self.vy * delta_time

        # 원형 시계판 외곽 테두리 안쪽으로 부드럽게 제한
        dx, dy = nx - ARENA_CX, ny - ARENA_CY
        dist = hypot(dx, dy)
        max_r = ARENA_RADIUS - PLAYER_RADIUS - 12.0
        if dist > max_r and dist > 0.0:
            scale = max_r / dist
            nx = ARENA_CX + dx * scale
            ny = ARENA_CY + dy * scale

        self.x, self.y = nx, ny
        if hypot(self.x - prev_x, self.y - prev_y) > 0.25:
            if abs(move_x) > abs(move_y):
                self.facing = "right" if move_x > 0 else "left"
            elif move_y != 0:
                self.facing = "up" if move_y > 0 else "down"
            self.animation_time += delta_time
            self.frame = int(self.animation_time * 8) % 4
            if self.frame != self.last_step_frame and self.frame in (1, 3):
                self.events.append(("step", self.x, self.y))
            self.last_step_frame = self.frame
        else:
            self.frame = 0
            self.last_step_frame = 0

        return "playing"


def _draw_decorative_gear(cx: float, cy: float, radius: float, teeth: int, angle: float, color: tuple[int, int, int]) -> None:
    draw_circle(cx, cy, int(radius), *color, 64)
    draw_circle(cx, cy, int(radius * 0.55), *color, 52)
    for idx in range(teeth):
        a = angle + idx * (2 * pi / teeth)
        draw_line(
            cx + cos(a) * (radius * 0.55), cy + sin(a) * (radius * 0.55),
            cx + cos(a) * (radius + 12), cy + sin(a) * (radius + 12),
            *color, 68,
        )


def draw_clock_tower(
    menu_font,
    hint_font,
    draw_centered_text: Callable,
    sprite: Image,
    run: ClockTowerRun,
) -> None:
    cx, cy = ARENA_CX, ARENA_CY
    pulse = 0.5 + 0.5 * sin(run.elapsed * 2.8)

    # 어두운 시계탑 석실 배경 + 좌우 장식 기어
    _fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (14, 14, 22))
    _draw_decorative_gear(220, 620, 118, 12, run.elapsed * 0.22, (112, 92, 62))
    _draw_decorative_gear(260, 260, 86, 10, -run.elapsed * 0.34, (92, 82, 64))
    _draw_decorative_gear(1380, 620, 118, 12, -run.elapsed * 0.22, (112, 92, 62))
    _draw_decorative_gear(1340, 260, 86, 10, run.elapsed * 0.34, (92, 82, 64))

    # 거대한 원형 시계판 아레나
    draw_circle(cx, cy, int(ARENA_RADIUS + 20), 42, 36, 34, filled=True)
    draw_circle(cx, cy, int(ARENA_RADIUS + 18), 186, 150, 90)
    draw_circle(cx, cy, int(ARENA_RADIUS + 8), 28, 30, 42, filled=True)
    draw_circle(cx, cy, int(ARENA_RADIUS + 2), 216, 178, 108)
    draw_circle(cx, cy, int(ARENA_RADIUS), 22, 26, 38, filled=True)

    # 시계판 내부 동심원 및 12시간 눈금
    draw_circle(cx, cy, int(ARENA_RADIUS * 0.72), 54, 62, 78)
    draw_circle(cx, cy, int(ARENA_RADIUS * 0.44), 48, 56, 72)
    for hour in range(12):
        angle = pi / 2 - hour * (pi / 6)
        major = hour % 3 == 0
        inner_r = ARENA_RADIUS - (42 if major else 26)
        outer_r = ARENA_RADIUS - 8
        col = (224, 186, 114) if major else (136, 122, 94)
        draw_line(
            cx + cos(angle) * inner_r, cy + sin(angle) * inner_r,
            cx + cos(angle) * outer_r, cy + sin(angle) * outer_r,
            *col,
        )
        if major:
            px, py = -sin(angle) * 2.0, cos(angle) * 2.0
            draw_line(
                cx + cos(angle) * inner_r + px, cy + sin(angle) * inner_r + py,
                cx + cos(angle) * outer_r + px, cy + sin(angle) * outer_r + py,
                *col,
            )

    # 정중앙 시계 코어 제단
    draw_circle(cx, cy, int(CORE_RADIUS + 6), 36, 34, 42, filled=True)
    draw_circle(cx, cy, int(CORE_RADIUS + 4), 192, 158, 96)
    draw_circle(cx, cy, int(CORE_RADIUS - 4), 24, 34, 48, filled=True)
    draw_circle(cx, cy, int(18 + 5 * pulse), 242, 198, 104, int(52 + 34 * pulse), filled=True)
    draw_circle(cx, cy, 10, 252, 224, 146, filled=True)

    # 주인공 렌더링
    draw_circle(run.x, run.y - 14, 14, 10, 10, 14, 150, filled=True)
    sprite.clip_draw(
        run.frame * SPRITE_FRAME_SIZE, SPRITE_ROWS[run.facing],
        SPRITE_FRAME_SIZE, SPRITE_FRAME_SIZE, run.x, run.y + 4, 70, 70,
    )

    # 상단 HUD 바
    _fill(18, 844, 1564, 46, (22, 20, 26, 238))
    draw_rectangle(18, 844, 1582, 890, 182, 150, 92, filled=False)
    menu_font.draw(36, 867, "Ⅲ. 멈춘 시계탑", (242, 212, 148))
    hint_font.draw(310, 866, "원형 시계판 아레나  (기초 구조)", (226, 216, 194))
    draw_centered_text(hint_font, "R 재시작  ·  ESC 일시정지", 1456, 866, (172, 188, 196))

    # 하단 안내 바
    if run.notice and run.elapsed < run.notice_until:
        _fill(260, 62, 1080, 40, (20, 20, 28, 234))
        draw_rectangle(260, 62, 1340, 102, 182, 150, 92, filled=False)
        draw_centered_text(hint_font, run.notice, SCREEN_WIDTH / 2, 82, (240, 224, 190))

    _fill(460, 14, 680, 34, (18, 20, 28, 224))
    draw_rectangle(460, 14, 1140, 48, 92, 88, 76, filled=False)
    draw_centered_text(
        hint_font,
        "방향키 / WASD 이동   ·   R 다시 시작   ·   ESC 일시정지",
        SCREEN_WIDTH / 2, 31, (180, 190, 198),
    )
