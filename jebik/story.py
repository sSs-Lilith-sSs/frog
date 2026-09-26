"""Cutscene hooks: which story cards to show and when (pure).

* game intro — before 1-1 the first time (per profile);
* between worlds — before the first level of world 2 / 3 the first time
  (the world's ``WorldDef.story`` cards);
* final — after winning 3-4 the first time: final card + credits.

A :class:`Card` names an i18n text and an illustration id. Illustrations are
drawn by ``jebik/scenes/story_art.py``; a world's art module may draw its own
cards via ``WorldArt.draw_story`` (the ``world`` field says whose art).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .worlds import all_worlds, world_of_level

if TYPE_CHECKING:
    from .save import Profile

FIRST_LEVEL = "1-1"
FINAL_LEVEL = "3-4"


@dataclass(frozen=True)
class Card:
    text_key: str             # i18n key ("" = no text, e.g. the credits roll)
    art: str                  # illustration id
    world: str | None = None  # world whose art may draw it


INTRO = (Card("story.intro.1", "intro"), Card("story.intro.2", "rule"))
FINAL = (Card("story.final.1", "final"), Card("", "credits"))


def world_cards(world_id: str) -> list[Card]:
    world = next(w for w in all_worlds() if w.id == world_id)
    return [Card(key, "world", world.id) for key in world.story]


def before_level(profile: "Profile | None", level_id: str) -> tuple[list[Card], str | None]:
    """Cards to show before ``level_id`` and the profile flag that marks them seen."""
    if profile is None or not level_id.endswith("-1"):
        return [], None
    world = world_of_level(level_id)
    if level_id == FIRST_LEVEL:
        flag = "story.intro"
        cards = list(INTRO) + world_cards(world.id)
    else:
        flag = f"story.{world.id}"
        cards = world_cards(world.id)
    if profile.has(flag) or not cards:
        return [], None
    return cards, flag


def after_level(profile: "Profile | None", level_id: str) -> tuple[list[Card], str | None]:
    """Cards after winning ``level_id`` (the finale after 3-4)."""
    if profile is None or level_id != FINAL_LEVEL or profile.has("story.final"):
        return [], None
    return list(FINAL), "story.final"


def credits_cards() -> list[Card]:
    return [Card("", "credits")]
