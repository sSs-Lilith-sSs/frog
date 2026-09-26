"""All game tunables in one place: timings, speeds, ranges, sizes and colours.

Logic modules (``jebik.game``) only read the numbers from here; nothing in this
file imports pygame, so it is safe to use from headless tests.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------- paths
PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"
FONT_DIR = ASSETS_DIR / "fonts"
AUDIO_DIR = ASSETS_DIR / "audio"
LEVELS_DIR = PACKAGE_DIR / "levels"
FONT_BOLD = FONT_DIR / "MPLUSRounded1c-Bold.ttf"
FONT_REGULAR = FONT_DIR / "MPLUSRounded1c-Regular.ttf"

# ---------------------------------------------------------------- display
SCREEN_W, SCREEN_H = 1920, 1080
FPS = 60
MAX_DT = 1 / 20            # clamp long frames so physics never explodes
HUD_H = 110
TRANSITION_TIME = 0.28     # scene cross-fade, seconds

# Field layout. The spec's base cell is 64 px (the biggest 22x14 level gets it);
# small early levels get bigger cells so the pond does not look lost.
MAX_CELL = 80
FIELD_MARGIN_X = 200       # min free space left/right of the field
FIELD_MARGIN_Y = 30        # min free space above/below the field (below HUD)

# Supersampling factors for the drawn art.
SS_SPRITE = 4              # small cached sprites (frog, flies, icons)
SS_FIELD = 2               # the numpy water field (soft anyway)
SS_BACKDROP = 2            # full-screen backdrops (menu, shores)

# ---------------------------------------------------------------- frog
HOP_TIME = 0.15            # one-cell hop animation
SUPERJUMP_TIME = 0.30      # two-cell super jump
SUPERJUMP_COOLDOWN = 3.0
HOLD_REPEAT_DELAY = 0.05   # extra pause between hops while a key is held
TONGUE_RANGE = 2
TONGUE_RANGE_FIREFLY = 4
TONGUE_COOLDOWN = 0.5
TONGUE_EXTEND_SPEED = 26.0   # cells per second
TONGUE_RETRACT_SPEED = 20.0
TONGUE_HOLD = 0.04           # pause at full extension
FIREFLY_DURATION = 5.0
INVULN_TIME = 2.0
SPLASH_TIME = 0.75         # frog is under water before respawning
HIT_STUN_TIME = 0.35       # frog cannot act right after a snake bite
MAX_HEARTS = 3
START_HEARTS = 3

# ---------------------------------------------------------------- flies
FLY_MIN, FLY_MAX = 3, 5            # counted flies (fly/dragonfly) on the field
FLY_RESPAWN_DELAY = (1.2, 2.6)
FLY_SPEED = 2.4                    # cells per second
DRAGON_SPEED = 5.0
FLY_HOP_RANGE = (1, 3)             # cells per flight
DRAGON_HOP_RANGE = (2, 5)
FLY_REST_CHANCE = 0.55             # chance to sit down after a flight
FLY_REST_TIME = (1.0, 2.0)
FLY_SHORT_PAUSE = (0.15, 0.45)
FLY_WATER_CHANCE = 0.22            # chance a flight target is over water
DRAGON_CHANCE = 0.14               # chance a new counted fly is a dragonfly
GOLD_INTERVAL = (22.0, 34.0)       # seconds between golden flies
FIREFLY_INTERVAL = (30.0, 40.0)    # seconds between fireflies
SPECIAL_LIFETIME = 13.0            # golden/firefly leave after this long

FLY_VALUE = {"fly": 1, "dragon": 2, "gold": 0, "firefly": 0}

# ---------------------------------------------------------------- snake
SNAKE_LENGTH = 4                   # head + body segments
SNAKE_CHASE_STEP = 0.27            # seconds per cell while chasing
SNAKE_WANDER_STEP = 0.46           # seconds per cell while wandering
SNAKE_SIGHT = 4                    # starts chasing within this Manhattan distance
SNAKE_LOSE_SIGHT = 6               # gives up beyond this distance
SNAKE_RETREAT_TIME = 2.6           # after biting, the snake backs off
SNAKE_SAFE_RESPAWN_DIST = 3        # respawn pad must be this far from the snake

# ---------------------------------------------------------------- scoring
SCORE_PER_FLY = 100
SCORE_PER_HEART = 200
SCORE_NO_DAMAGE = 500
WIN_DELAY = 0.9                    # celebration before the win panel
LOSE_DELAY = 0.9

# ---------------------------------------------------------------- audio
MUSIC_TRACKS = ("A", "B", "C")
MUSIC_FILES = {"A": "music_a.wav", "B": "music_b.wav", "C": "music_c.wav"}
SFX_NAMES = ("jump", "tongue", "eat", "splash", "hit", "win", "lose",
             "superjump", "powerup", "click", "overeat", "full", "denied", "tick")
DEFAULT_SETTINGS = {
    "lang": "ua",
    "music_volume": 0.6,
    "sfx_volume": 0.8,
    "music_track": "B",
    "fullscreen": False,
    "show_grid": False,
}

# ---------------------------------------------------------------- colours
C_INK = (30, 80, 30)            # dark green outline / text on light buttons
C_INK_SOFT = (40, 90, 50)
C_BUTTON = (250, 250, 240)
C_BUTTON_HOT = (255, 215, 90)
C_BUTTON_SHADOW = (30, 90, 40)
C_BUTTON_DISABLED = (205, 210, 200)
C_TITLE = (120, 220, 90)
C_TITLE_OUTLINE = (30, 80, 30)
C_SUBTITLE_OUTLINE = (200, 80, 120)
C_WHITE = (255, 255, 255)
C_HUD_BG = (25, 45, 40)
C_HUD_LINE = (120, 220, 90)
C_HUD_TEXT = (235, 235, 235)
C_HUD_SUB = (170, 210, 170)
C_HUD_COUNTER = (255, 220, 110)
C_HUD_HINT = (200, 200, 170)
C_HUD_MUTED = (170, 190, 170)
C_HEART = (225, 50, 65)
C_HEART_EMPTY = (80, 80, 80)
C_FIELD_BORDER = (30, 80, 90)
C_POND_TOP = (80, 170, 195)
C_POND_BOTTOM = (45, 125, 170)
C_PANEL = (250, 248, 236)
C_DIM = (10, 25, 30, 150)
C_STAR = (255, 205, 60)
C_STAR_EMPTY = (205, 200, 185)
C_RED_TEXT = (220, 60, 70)
C_GOOD = (120, 220, 90)
