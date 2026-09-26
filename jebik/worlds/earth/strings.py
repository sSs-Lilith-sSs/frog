"""Earth-world strings (UA, EN, RU). Keys must start with ``earth.``."""
from __future__ import annotations

STRINGS: dict[str, tuple[str, str, str]] = {
    "earth.exit_hint": ("стрибай у нору", "hop into the burrow", "прыгай в нору"),
    "earth.name": ("Земля", "Land", "Земля"),
    "earth.boss": ("Кабан", "Boar", "Кабан"),
    "earth.hit": ("БУМ!", "BONK!", "БУМ!"),
    "earth.story.1": ("Ставок позаду! Далі — луки й поля: трава, ями, а в норах хтось шарудить...",
                      "The pond is behind! Next come meadows and fields: grass, pits, and "
                      "something rustling in the burrows...",
                      "Пруд позади! Дальше — луга и поля: трава, ямы, а в норах кто-то шуршит..."),
    "earth.story.2": ("Кажуть, на краю поля живе Кабан. Тупотить так, що земля осипається. "
                      "Заманюй його в пні!",
                      "They say a Boar lives at the edge of the field. He stomps so hard the "
                      "ground crumbles. Lure him into the stumps!",
                      "Говорят, на краю поля живёт Кабан. Топает так, что земля осыпается. "
                      "Заманивай его в пни!"),
    "earth.hint.hedgehog": ("Їжак котиться прямо — зійди з його рядка!",
                            "The hedgehog rolls straight — leave its row!",
                            "Ёжик катится прямо — уйди с его ряда!"),
    "earth.hint.fox": ("Лисиця перестрибує ями, але потім секунду оговтується",
                       "The fox leaps over pits, then needs a second to recover",
                       "Лиса перепрыгивает ямы, но потом секунду приходит в себя"),
    "earth.hint.mole": ("Земля тремтить — стрибай геть!", "The ground trembles — hop away!",
                        "Земля дрожит — прыгай прочь!"),
    "earth.hint.boar": ("Заманюй Кабана в пень і бий язиком, поки він оглушений",
                        "Lure the Boar into a stump and tongue him while he is stunned",
                        "Заманивай Кабана в пень и бей языком, пока он оглушён"),
}
