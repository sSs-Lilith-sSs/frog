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
    "water.boss": ("Кит", "Whale", "Кит"),
    "water.whale_hit": ("ПИРХ!", "PFFT!", "ПФФ!"),
    "water.pike": ("Щука", "Pike", "Щука"),
    "water.heron": ("Чапля", "Heron", "Цапля"),
    "water.hint.pike": ("бульбашки біля латаття — стрибай геть!",
                        "bubbles by the pad — hop away!",
                        "пузырьки у кувшинки — прыгай прочь!"),
    "water.hint.heron": ("тінь під тобою — тікай!",
                         "a shadow under you — run!",
                         "тень под тобой — беги!"),
    "water.hint.whale": ("стань на спину кита і лизни дихало",
                         "stand on the whale's back and lick the blowhole",
                         "встань на спину кита и лизни дыхало"),
}
