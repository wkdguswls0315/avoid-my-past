"""3번째 미니게임: 'Ⅲ. 멈춘 시계탑' — 원형 시계판 아레나 & 시간 정지 액션."""

from __future__ import annotations

from dataclasses import dataclass
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
SPAWN_GRACE = 1.2
GEAR_PICKUP_RADIUS = 28.0

SPRITE_FRAME_SIZE = 320
SPRITE_ROWS = {
    "down": 3 * SPRITE_FRAME_SIZE,
    "left": 2 * SPRITE_FRAME_SIZE,
    "right": SPRITE_FRAME_SIZE,
    "up": 0,
}


@dataclass(frozen=True)
class HandSpec:
    length: float
    speed: float        # rad/s (음수 = 시계 방향, 양수 = 반시계 방향)
    start_angle: float  # 초기 각도 (rad)
    thickness: float
    color: tuple[int, int, int]


@dataclass(frozen=True)
class ClockStage:
    title: str
    subtitle: str
    time_limit: float
    hands: tuple[HandSpec, ...]
    gear_polar: tuple[tuple[float, float], ...]  # (반지름 비율 0..1, 각도 deg)


CLOCK_STAGES: tuple[ClockStage, ...] = (
    ClockStage(
        title="1라운드 · 깨어나는 초침",
        subtitle="돌아가는 시계 바늘을 피해 태엽 3개를 모두 주운 뒤 중앙 코어에 꽂으세요!",
        time_limit=26.0,
        hands=(
            HandSpec(ARENA_RADIUS - 16, -0.92, pi / 2, 10.0, (248, 122, 102)),
        ),
        gear_polar=(
            (0.66, 90.0),
            (0.68, 210.0),
            (0.68, 330.0),
        ),
    ),
)


def _fill(x: float, y: float, width: float, height: float, color: tuple[int, ...]) -> None:
    draw_rectangle(
        int(x), int(y), int(x + width) - 1, int(y + height) - 1, *color, filled=True
    )


def _approach(current: float, target: float, delta: float) -> float:
    if current < target:
        return min(target, current + delta)
    return max(target, current - delta)


def _polar_to_xy(radius_ratio: float, angle_deg: float) -> tuple[float, float]:
    rad = angle_deg * pi / 180.0
    dist = ARENA_RADIUS * radius_ratio
    return ARENA_CX + cos(rad) * dist, ARENA_CY + sin(rad) * dist


def _point_segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    abx, aby = bx - ax, by - ay
    denom = abx * abx + aby * aby
    if denom <= 1e-9:
        return hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / denom))
    cx, cy = ax + abx * t, ay + aby * t
    return hypot(px - cx, py - cy)


class ClockTowerRun:
    """Manage circular clock-arena player movement, sweeping hands, gears, and core return."""

    def __init__(self) -> None:
        self.stage_index = 0
        self.elapsed = 0.0
        self.world_clock = 0.0
        self.events: list[tuple[str, float, float]] = []
        self.notice = ""
        self.notice_until = 0.0
        self.gears: list[tuple[float, float]] = []
        self.collected_gears = 0
        self.hand_angles: list[float] = []
        self.reset_all()

    @property
    def stage(self) -> ClockStage:
        return CLOCK_STAGES[self.stage_index]

    @property
    def stage_count(self) -> int:
        return len(CLOCK_STAGES)

    @property
    def total_gears(self) -> int:
        return len(self.stage.gear_polar)

    @property
    def core_ready(self) -> bool:
        return len(self.gears) == 0

    def reset_all(self) -> None:
        self.stage_index = 0
        self.begin_round()

    def begin_round(self, notice: str | None = None) -> None:
        st = self.stage
        self.x = ARENA_CX
        self.y = ARENA_CY - 220.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing = "up"
        self.frame = 0
        self.animation_time = 0.0
        self.last_step_frame = 0
        self.elapsed = 0.0
        self.world_clock = 0.0
        self.gears = [_polar_to_xy(r, deg) for r, deg in st.gear_polar]
        self.collected_gears = 0
        self.hand_angles = [hand.start_angle for hand in st.hands]
        self.notice = st.subtitle if notice is None else notice
        self.notice_until = 4.2

    def update(self, move_x: int, move_y: int, delta_time: float) -> str:
        self.events.clear()
        if delta_time <= 0.0:
            return "playing"
        self.elapsed += delta_time
        self.world_clock += delta_time

        # 시계 바늘 회전 갱신
        for idx, hand in enumerate(self.stage.hands):
            self.hand_angles[idx] += hand.speed * delta_time

        # 플레이어 이동
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

        # 1) 시계 바늘 피격 판정 (초반 무적 시간 이후 & 코어 외곽)
        if self.elapsed >= SPAWN_GRACE:
            for hand, angle in zip(self.stage.hands, self.hand_angles):
                sx = ARENA_CX + cos(angle) * (CORE_RADIUS + 8.0)
                sy = ARENA_CY + sin(angle) * (CORE_RADIUS + 8.0)
                ex = ARENA_CX + cos(angle) * hand.length
                ey = ARENA_CY + sin(angle) * hand.length
                hit_dist = _point_segment_distance(self.x, self.y, sx, sy, ex, ey)
                if hit_dist <= PLAYER_RADIUS + hand.thickness * 0.55:
                    hx, hy = self.x, self.y
                    self.begin_round("시계 바늘에 스쳤습니다! 현재 라운드를 다시 시작합니다.")
                    self.events.append(("hit", hx, hy))
                    return "reset"

        # 2) 제한 시간 초과 판정
        if self.elapsed >= self.stage.time_limit:
            hx, hy = self.x, self.y
            self.begin_round("시간이 다 되었습니다! 더 빠르게 태엽을 회수하세요.")
            self.events.append(("timeout", hx, hy))
            return "reset"

        # 3) 부서진 태엽 조각 수집
        remaining_gears: list[tuple[float, float]] = []
        for gx, gy in self.gears:
            if hypot(self.x - gx, self.y - gy) <= GEAR_PICKUP_RADIUS:
                self.collected_gears += 1
                self.events.append(("gear", gx, gy))
            else:
                remaining_gears.append((gx, gy))
        if len(remaining_gears) != len(self.gears):
            self.gears = remaining_gears
            if not self.gears:
                self.notice = "모든 태엽을 모았습니다! 정중앙 시계 코어에 꽂으세요!"
                self.notice_until = self.elapsed + 3.5

        # 4) 모든 태엽 수집 후 중앙 코어 도착 -> 라운드 통과
        if self.core_ready and hypot(self.x - ARENA_CX, self.y - ARENA_CY) <= CORE_RADIUS + 8.0:
            if self.stage_index + 1 >= len(CLOCK_STAGES):
                self.events.append(("clear", ARENA_CX, ARENA_CY))
                return "clear"
            self.events.append(("next", ARENA_CX, ARENA_CY))
            self.stage_index += 1
            self.begin_round()
            return "next"

        return "playing"


def _draw_decorative_gear(
    cx: float, cy: float, radius: float, teeth: int, angle: float, color: tuple[int, int, int]
) -> None:
    draw_circle(cx, cy, int(radius), *color, 64)
    draw_circle(cx, cy, int(radius * 0.55), *color, 52)
    for idx in range(teeth):
        a = angle + idx * (2 * pi / teeth)
        draw_line(
            cx + cos(a) * (radius * 0.55), cy + sin(a) * (radius * 0.55),
            cx + cos(a) * (radius + 12), cy + sin(a) * (radius + 12),
            *color, 68,
        )


def _draw_pickup_gear(gx: float, gy: float, elapsed: float) -> None:
    pulse = 0.5 + 0.5 * sin(elapsed * 4.5 + gx * 0.02)
    spin = elapsed * 1.8
    draw_circle(gx, gy, int(22 + 4 * pulse), 255, 206, 92, int(44 + 28 * pulse), filled=True)
    draw_circle(gx, gy, 14, 248, 206, 108)
    draw_circle(gx, gy, 6, 36, 30, 26, filled=True)
    draw_circle(gx, gy, 6, 255, 232, 156)
    for tooth in range(6):
        ang = spin + tooth * (pi / 3)
        tx = gx + cos(ang) * 15
        ty = gy + sin(ang) * 15
        _fill(tx - 3, ty - 3, 6, 6, (255, 224, 128))


def _draw_clock_hand(hand: HandSpec, angle: float, harmless: bool) -> None:
    cos_a, sin_a = cos(angle), sin(angle)
    px, py = -sin_a, cos_a
    start_r = CORE_RADIUS + 6.0
    sx, sy = ARENA_CX + cos_a * start_r, ARENA_CY + sin_a * start_r
    ex, ey = ARENA_CX + cos_a * hand.length, ARENA_CY + sin_a * hand.length

    outer_alpha = 95 if harmless else 190
    core_alpha = 140 if harmless else 255
    half_w = int(hand.thickness * 0.55)
    for off in range(-half_w, half_w + 1):
        draw_line(
            sx + px * off, sy + py * off,
            ex + px * off, ey + py * off,
            *hand.color, outer_alpha,
        )
    draw_line(sx, sy, ex, ey, 255, 242, 220, core_alpha)
    draw_circle(ex, ey, int(hand.thickness * 0.65), *hand.color, core_alpha, filled=True)


def draw_clock_tower(
    menu_font,
    hint_font,
    draw_centered_text: Callable,
    sprite: Image,
    run: ClockTowerRun,
) -> None:
    cx, cy = ARENA_CX, ARENA_CY
    pulse = 0.5 + 0.5 * sin(run.elapsed * 3.4)

    # 어두운 시계탑 석실 배경 + 좌우 장식 기어
    _fill(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (14, 14, 22))
    _draw_decorative_gear(220, 620, 118, 12, run.world_clock * 0.22, (112, 92, 62))
    _draw_decorative_gear(260, 260, 86, 10, -run.world_clock * 0.34, (92, 82, 64))
    _draw_decorative_gear(1380, 620, 118, 12, -run.world_clock * 0.22, (112, 92, 62))
    _draw_decorative_gear(1340, 260, 86, 10, run.world_clock * 0.34, (92, 82, 64))

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

    # 정중앙 시계 코어 제단 (태엽 다 모으면 청록빛으로 활성화!)
    core_border = (122, 236, 198) if run.core_ready else (192, 158, 96)
    core_glow = (118, 236, 198) if run.core_ready else (242, 198, 104)
    draw_circle(cx, cy, int(CORE_RADIUS + 6), 36, 34, 42, filled=True)
    draw_circle(cx, cy, int(CORE_RADIUS + 4), *core_border)
    draw_circle(cx, cy, int(CORE_RADIUS - 4), 24, 34, 48, filled=True)
    if run.core_ready:
        draw_circle(cx, cy, int(CORE_RADIUS + 14 + 8 * pulse), *core_glow, int(90 + 70 * pulse))
    draw_circle(cx, cy, int(20 + 6 * pulse), *core_glow, int(60 + 38 * pulse), filled=True)
    draw_circle(cx, cy, 10, 245, 252, 236 if run.core_ready else 146, filled=True)

    # 태엽 조각들
    for gx, gy in run.gears:
        _draw_pickup_gear(gx, gy, run.elapsed)

    # 회전 시계 바늘들
    harmless = run.elapsed < SPAWN_GRACE
    for hand, angle in zip(run.stage.hands, run.hand_angles):
        _draw_clock_hand(hand, angle, harmless)

    # 주인공 렌더링 (초반 무적 시간엔 연한 보호 링 표시)
    if harmless:
        draw_circle(run.x, run.y, 26, 152, 224, 232, 145)
    draw_circle(run.x, run.y - 14, 14, 10, 10, 14, 150, filled=True)
    sprite.clip_draw(
        run.frame * SPRITE_FRAME_SIZE, SPRITE_ROWS[run.facing],
        SPRITE_FRAME_SIZE, SPRITE_FRAME_SIZE, run.x, run.y + 4, 70, 70,
    )

    # 상단 HUD 바
    _fill(18, 844, 1564, 46, (22, 20, 26, 238))
    draw_rectangle(18, 844, 1582, 890, 182, 150, 92, filled=False)
    menu_font.draw(36, 867, "Ⅲ. 멈춘 시계탑", (242, 212, 148))
    hint_font.draw(300, 866, f"{run.stage.title}  ({run.stage_index + 1}/{run.stage_count})", (232, 220, 196))

    remaining = max(0, int(run.stage.time_limit - run.elapsed + 0.999))
    low_time = remaining <= 8
    time_col = (255, 112, 104) if (low_time and int(run.elapsed * 4) % 2 == 0) else (
        (248, 166, 112) if low_time else (224, 214, 192)
    )
    hint_font.draw(720, 866, f"TIME {remaining:02d}s", time_col)

    gear_text = "코어로 이동!" if run.core_ready else f"태엽  {run.collected_gears}/{run.total_gears}"
    gear_col = (122, 236, 198) if run.core_ready else (255, 214, 110)
    hint_font.draw(880, 866, gear_text, gear_col)

    draw_centered_text(hint_font, "R 재시작  ·  ESC 일시정지", 1456, 866, (172, 188, 196))

    # 하단 안내 바
    if run.notice and run.elapsed < run.notice_until:
        _fill(240, 62, 1120, 40, (20, 20, 28, 234))
        draw_rectangle(240, 62, 1360, 102, 182, 150, 92, filled=False)
        draw_centered_text(hint_font, run.notice, SCREEN_WIDTH / 2, 82, (240, 224, 190))

    _fill(460, 14, 680, 34, (18, 20, 28, 224))
    draw_rectangle(460, 14, 1140, 48, 92, 88, 76, filled=False)
    draw_centered_text(
        hint_font,
        "방향키 / WASD 이동   ·   R 다시 시작   ·   ESC 일시정지",
        SCREEN_WIDTH / 2, 31, (180, 190, 198),
    )
