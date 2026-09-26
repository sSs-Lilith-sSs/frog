"""Earth-world strings (UA, EN, RU). Keys must start with ``earth.``."""
from __future__ import annotations

STRINGS: dict[str, tuple[str, str, str]] = {
    "earth.exit_hint": ("стрибай у нору", "hop into the burrow", "прыгай в нору"),
    "earth.name": ("Земля", "Land", "Земля"),
    "earth.story.1": ("Ставок позаду! Далі — луки й поля: трава, ями, а в норах хтось шарудить...",
                      "The pond is behind! Next come meadows and fields: grass, pits, and "
                      "something rustling in the burrows...",
                      "Пруд позади! Дальше — луга и поля: трава, ямы, а в норах кто-то шуршит..."),
    # TODO(earth agent): "earth.boss" (boar name for the HUD pill), enemy hints
}
