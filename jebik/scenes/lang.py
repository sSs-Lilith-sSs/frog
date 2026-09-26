"""UA / EN / RU pills (top-right corner, as in the menu mockup)."""
from __future__ import annotations

from typing import Callable

from .. import config, i18n
from ..ui.widgets import Button


class LangPill(Button):
    def colors(self):
        if self.selected and self.selected():
            return config.C_BUTTON_HOT, config.C_INK_SOFT
        if self.hot:
            return (255, 240, 190), config.C_INK_SOFT
        return (255, 255, 255), config.C_INK_SOFT


def lang_pills(app, on_change: Callable[[], None] | None = None) -> list[Button]:
    pills = []
    for i, code in enumerate(i18n.LANGS):
        def pick(c=code):
            if app.settings["lang"] != c:
                app.set_lang(c)
                if on_change:
                    on_change()
        pills.append(LangPill((1560 + i * 110, 36, 96, 64), i18n.LANG_LABELS[code], pick, size=30,
                              selected=lambda c=code: app.settings["lang"] == c, arrow=False,
                              radius=20, shadow=0, border=3))
    return pills
