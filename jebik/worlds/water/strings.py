"""Water-world strings (UA, EN, RU). Keys must start with ``water.``."""
from __future__ import annotations

STRINGS: dict[str, tuple[str, str, str]] = {
    "water.exit_hint": ("стрибай на лотос", "hop onto the lotus", "прыгай на лотос"),
    "water.name": ("Вода", "Water", "Вода"),
    "water.story.1": ("Жабка вирушає в мандри! Спершу — рідний ставок: латаття, мухи і змія, "
                      "що не вміє плавати.",
                      "The frog sets off on a journey! First, her home pond: lily pads, flies "
                      "and a snake that can't swim.",
                      "Жабка отправляется в путешествие! Сначала — родной пруд: кувшинки, мухи "
                      "и змея, которая не умеет плавать."),
    # TODO(water agent): "water.boss" (whale name for the HUD pill), hints for pike / heron
}
