"""UI strings in Ukrainian, English and Russian.

Usage: ``i18n.set_lang("en"); i18n.t("menu.play")``. Title and subtitle are
the same in every language by design.
"""
from __future__ import annotations

LANGS = ("ua", "en", "ru")
LANG_LABELS = {"ua": "UA", "en": "EN", "ru": "RU"}

TITLE = "жэбик"
SUBTITLE = "для любимой кыци (=^・ω・^=)"

# key: (ua, en, ru)
_S: dict[str, tuple[str, str, str]] = {
    # --- main menu
    "menu.play": ("Грати", "Play", "Играть"),
    "menu.levels": ("Вибір рівня", "Level select", "Выбор уровня"),
    "menu.records": ("Рекорди", "Records", "Рекорды"),
    "menu.settings": ("Налаштування", "Settings", "Настройки"),
    "menu.howto": ("Як грати", "How to play", "Как играть"),
    "menu.quit": ("Вихід", "Quit", "Выход"),
    "menu.player": ("Гравець: {name}", "Player: {name}", "Игрок: {name}"),
    # --- common
    "common.back": ("Назад", "Back", "Назад"),
    "common.soon": ("скоро", "soon", "скоро"),
    "common.yes": ("Так", "Yes", "Да"),
    "common.no": ("Ні", "No", "Нет"),
    "common.cancel": ("Скасувати", "Cancel", "Отмена"),
    "common.hint_nav": ("Стрілки — вибір · Enter — ок · Esc — назад",
                        "Arrows — select · Enter — OK · Esc — back",
                        "Стрелки — выбор · Enter — ок · Esc — назад"),
    # --- profiles
    "profile.title": ("Хто грає?", "Who is playing?", "Кто играет?"),
    "profile.new": ("Новий профіль", "New profile", "Новый профиль"),
    "profile.create": ("Створити", "Create", "Создать"),
    "profile.enter_name": ("Введи ім'я:", "Enter your name:", "Введи имя:"),
    "profile.placeholder": ("ім'я...", "name...", "имя..."),
    "profile.delete_q": ("Видалити профіль «{name}»?", "Delete profile “{name}”?",
                         "Удалить профиль «{name}»?"),
    "profile.err_empty": ("Ім'я не може бути порожнім", "Name can't be empty",
                          "Имя не может быть пустым"),
    "profile.err_exists": ("Такий профіль уже є", "This profile already exists",
                           "Такой профиль уже есть"),
    "profile.hint": ("Delete — видалити профіль", "Delete — remove profile",
                     "Delete — удалить профиль"),
    # --- difficulty
    "diff.title": ("Складність", "Difficulty", "Сложность"),
    "diff.ezzz_desc": ("3 серця · без таймера\nзолота муха: +1 серце",
                       "3 hearts · no timer\ngolden fly: +1 heart",
                       "3 сердца · без таймера\nзолотая муха: +1 сердце"),
    "diff.tobi_desc": ("без сердець · таймер\nудар = рестарт рівня",
                       "no hearts · timer\none hit = restart",
                       "без сердец · таймер\nудар = рестарт уровня"),
    "diff.locked": ("після EZZZ", "after EZZZ", "после EZZZ"),
    # --- level select
    "levels.title": ("Вибір рівня", "Level select", "Выбор уровня"),
    "world.1": ("Вода", "Water", "Вода"),
    "world.2": ("Земля", "Land", "Земля"),
    "world.3": ("Небо", "Sky", "Небо"),
    "levels.best": ("рекорд {score}", "best {score}", "рекорд {score}"),
    "levels.locked": ("закрито", "locked", "закрыто"),
    # --- records
    "records.title": ("Рекорди", "Records", "Рекорды"),
    "records.soon": ("Таблиця рекордів з'явиться скоро!", "The records table is coming soon!",
                     "Таблица рекордов появится скоро!"),
    # --- settings
    "settings.title": ("Налаштування", "Settings", "Настройки"),
    "settings.music_volume": ("Гучність музики", "Music volume", "Громкость музыки"),
    "settings.sfx_volume": ("Гучність звуків", "Sound volume", "Громкость звуков"),
    "settings.music": ("Музика", "Music", "Музыка"),
    "settings.music_a": ("8-біт", "8-bit", "8-бит"),
    "settings.music_b": ("мультяшна", "cartoon", "мультяшная"),
    "settings.music_c": ("болотна полька", "swamp polka", "болотная полька"),
    "settings.fullscreen": ("Повний екран", "Fullscreen", "Полный экран"),
    "settings.grid": ("Показувати сітку", "Show grid", "Показывать сетку"),
    "settings.language": ("Мова", "Language", "Язык"),
    "settings.on": ("так", "on", "да"),
    "settings.off": ("ні", "off", "нет"),
    # --- how to play
    "howto.title": ("Як грати", "How to play", "Как играть"),
    "howto.move": ("Стрибок на 1 клітинку", "Hop 1 cell", "Прыжок на 1 клетку"),
    "howto.move_keys": ("стрілки або WASD", "arrows or WASD", "стрелки или WASD"),
    "howto.super": ("Суперстрибок через клітинку", "Super jump over a cell",
                    "Суперпрыжок через клетку"),
    "howto.super_keys": ("Shift + напрям · раз на 3 с", "Shift + direction · every 3 s",
                         "Shift + направление · раз в 3 с"),
    "howto.tongue": ("Язик ловить муху за 2 клітинки", "Tongue catches a fly 2 cells away",
                     "Язык ловит муху за 2 клетки"),
    "howto.tongue_keys": ("пробіл · пробіл + стрілка — в інший бік",
                          "Space · Space + arrow — another way",
                          "пробел · пробел + стрелка — в другую сторону"),
    "howto.goal": ("З'їж рівно N мух — з'явиться лотос-вихід",
                   "Eat exactly N flies — the lotus exit appears",
                   "Съешь ровно N мух — появится лотос-выход"),
    "howto.goal_sub": ("зайва муха забирає серце!", "an extra fly costs a heart!",
                       "лишняя муха отнимает сердце!"),
    "howto.flies": ("Муха +1 · бабка +2", "Fly +1 · dragonfly +2", "Муха +1 · стрекоза +2"),
    "howto.bonus": ("Золота муха — серце · світлячок — довгий язик",
                    "Golden fly — heart · firefly — long tongue",
                    "Золотая муха — сердце · светлячок — длинный язык"),
    "howto.danger": ("Не падай у воду і тікай від змії", "Don't fall in the water, flee the snake",
                     "Не падай в воду и беги от змеи"),
    "howto.danger_sub": ("вона не плаває — перестрибни воду!", "it can't swim — jump over water!",
                         "она не плавает — перепрыгни воду!"),
    "howto.pause": ("Esc — пауза", "Esc — pause", "Esc — пауза"),
    # --- game / HUD
    "game.level_name": ("Світ {w} · Рівень {l}", "World {w} · Level {l}", "Мир {w} · Уровень {l}"),
    "game.need_exact": ("треба рівно {n}", "need exactly {n}", "нужно ровно {n}"),
    "game.pause_hint": ("Esc — пауза", "Esc — pause", "Esc — пауза"),
    "game.full": ("Сита!", "Full!", "Сытая!"),
    "game.full_sub": ("стрибай на лотос", "hop onto the lotus", "прыгай на лотос"),
    "game.overeat": ("Обжерлась!", "Overate!", "Обожралась!"),
    "game.go": ("Злови {n} мух!", "Catch {n} flies!", "Поймай {n} мух!"),
    "game.max_hearts": ("серця повні", "hearts full", "сердца полны"),
    "game.long_tongue": ("довгий язик!", "long tongue!", "длинный язык!"),
    # --- pause
    "pause.title": ("Пауза", "Paused", "Пауза"),
    "pause.resume": ("Продовжити", "Resume", "Продолжить"),
    "pause.restart": ("Заново", "Restart", "Заново"),
    "pause.settings": ("Налаштування", "Settings", "Настройки"),
    "pause.menu": ("Меню", "Menu", "Меню"),
    # --- win / lose
    "win.title": ("Перемога!", "Victory!", "Победа!"),
    "win.score": ("Очки", "Score", "Очки"),
    "win.time": ("Час", "Time", "Время"),
    "win.best": ("Новий рекорд!", "New record!", "Новый рекорд!"),
    "win.next": ("Далі", "Next", "Дальше"),
    "win.again": ("Ще раз", "Again", "Ещё раз"),
    "win.menu": ("Меню", "Menu", "Меню"),
    "win.no_damage": ("без ударів", "no damage", "без ударов"),
    "win.par": ("швидко: до {t}", "fast: under {t}", "быстро: до {t}"),
    "lose.title": ("Ой-ой...", "Oh no...", "Ой-ой..."),
    "lose.sub": ("Серця скінчилися. Спробуй ще!", "Out of hearts. Try again!",
                 "Сердца закончились. Попробуй ещё!"),
}

_LANG_INDEX = {code: i for i, code in enumerate(LANGS)}
_current = "ua"


def set_lang(code: str) -> None:
    global _current
    _current = code if code in _LANG_INDEX else "ua"


def get_lang() -> str:
    return _current


def keys() -> list[str]:
    return list(_S)


def raw(key: str) -> tuple[str, str, str]:
    return _S[key]


def t(key: str, lang: str | None = None, **fmt: object) -> str:
    """Translate ``key``; missing keys fall back to the key itself."""
    entry = _S.get(key)
    if entry is None:
        return key
    text = entry[_LANG_INDEX.get(lang or _current, 0)]
    return text.format(**fmt) if fmt else text
