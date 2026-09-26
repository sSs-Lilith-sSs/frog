"""Sky-world strings (UA, EN, RU). Keys must start with ``sky.``."""
from __future__ import annotations

STRINGS: dict[str, tuple[str, str, str]] = {
    "sky.exit_hint": ("стрибай на веселку", "hop onto the rainbow", "прыгай на радугу"),
    "sky.name": ("Небо", "Sky", "Небо"),
    "sky.story.1": ("Жабка стрибнула так високо, що опинилась на рожевих хмаринках. "
                    "Обережно: деякі пливуть, а деякі тануть!",
                    "The frog jumped so high she landed on pink clouds. Careful: some "
                    "drift and some melt!",
                    "Жабка прыгнула так высоко, что оказалась на розовых облачках. "
                    "Осторожно: некоторые плывут, а некоторые тают!"),
    "sky.sasat": ("SASAT!", "SASAT!", "SASAT!"),
    # TODO(sky agent): "sky.boss" (HUD pill name), enemy hints
}
