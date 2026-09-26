"""UI strings in Ukrainian, English and Russian.

Usage: ``i18n.set_lang("en"); i18n.t("menu.play")``. Title and subtitle are
the same in every language by design.

World packages keep their own strings in ``jebik/worlds/<id>/strings.py``
(keys prefixed ``<id>.``); they are merged in automatically on first use.
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
    "levels.best": ("рекорд {score}", "best {score}", "рекорд {score}"),
    "levels.locked": ("закрито", "locked", "закрыто"),
    "levels.world": ("Світ {n}", "World {n}", "Мир {n}"),
    # --- records
    "records.title": ("Рекорди", "Records", "Рекорды"),
    "records.total": ("Загалом", "Total", "Всего"),
    "records.level": ("Рівень {id}", "Level {id}", "Уровень {id}"),
    "records.empty": ("Тут ще нікого немає — пройди рівень!", "Nobody here yet — beat the level!",
                      "Тут ещё никого нет — пройди уровень!"),
    "records.name": ("Гравець", "Player", "Игрок"),
    "records.score": ("Очки", "Score", "Очки"),
    "records.time": ("Час", "Time", "Время"),
    "records.stars": ("Зірки", "Stars", "Звёзды"),
    "records.levels": ("рівнів: {n}", "levels: {n}", "уровней: {n}"),
    "records.hint": ("←/→ — рівень · Tab — складність · Esc — назад",
                     "←/→ — level · Tab — difficulty · Esc — back",
                     "←/→ — уровень · Tab — сложность · Esc — назад"),
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
    "settings.touch": ("Сенсорне керування", "Touch controls", "Сенсорное управление"),
    "settings.touch_auto": ("Авто", "Auto", "Авто"),
    "settings.touch_on": ("Увімк", "On", "Вкл"),
    "settings.touch_off": ("Вимк", "Off", "Выкл"),
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
    "game.time_bonus": ("+{n} с", "+{n} s", "+{n} с"),
    "game.oops": ("Ой!", "Oops!", "Ой!"),
    "game.again": ("ще раз!", "again!", "ещё раз!"),
    "game.boss_defeated": ("Переможено!", "Defeated!", "Побеждён!"),
    "game.full_boss": ("а тепер — бос!", "now the boss!", "а теперь — босс!"),
    "boss.generic": ("Бос", "Boss", "Босс"),
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
    "lose.timeout": ("Час вийшов! Спробуй ще!", "Time's up! Try again!", "Время вышло! Попробуй ещё!"),
    # --- story / cutscenes
    "story.continue": ("Enter / тап — далі · Esc — пропустити", "Enter / tap — next · Esc — skip",
                       "Enter / тап — дальше · Esc — пропустить"),
    "story.intro.1": ("Жила-була жабка. Вона дуже любила мух — і ще більше любила пригоди.",
                      "Once upon a time there was a frog. She loved flies — and loved adventures "
                      "even more.",
                      "Жила-была жабка. Она очень любила мух — и ещё больше любила приключения."),
    "story.intro.2": ("Але жабка знає правило: з'їсти треба рівно стільки, скільки треба. "
                      "Ні мухою більше!",
                      "But the frog knows the rule: eat exactly as many as you need. Not one "
                      "fly more!",
                      "Но жабка знает правило: съесть надо ровно столько, сколько надо. "
                      "Ни мухой больше!"),
    "story.final.1": ("Жабка пройшла воду, землю і небо. Вона сита, щаслива і трохи втомилась.",
                      "The frog crossed water, land and sky. She is full, happy and a little "
                      "tired.",
                      "Жабка прошла воду, землю и небо. Она сыта, счастлива и немного устала."),
    "credits.title": ("Кінець", "The End", "Конец"),
    "credits.made": ("Графіка, музика і код — згенеровані з любов'ю",
                     "Art, music and code — generated with love",
                     "Графика, музыка и код — сгенерированы с любовью"),
    "credits.font": ("Шрифт: M PLUS Rounded 1c (OFL)", "Font: M PLUS Rounded 1c (OFL)",
                     "Шрифт: M PLUS Rounded 1c (OFL)"),
    "credits.thanks": ("Дякуємо за гру!", "Thanks for playing!", "Спасибо за игру!"),
}

_LANG_INDEX = {code: i for i, code in enumerate(LANGS)}
_current = "ua"
_worlds_merged = False


def register(strings: dict[str, tuple[str, str, str]]) -> None:
    """Add strings (e.g. of a world package); a key may not be redefined."""
    for key, entry in strings.items():
        if key in _S and _S[key] != entry:
            raise ValueError(f"i18n key {key!r} defined twice")
        _S[key] = entry


def _ensure_worlds() -> None:
    global _worlds_merged
    if _worlds_merged:
        return
    _worlds_merged = True
    from .worlds import all_worlds
    for world in all_worlds():
        register(world.strings)


def set_lang(code: str) -> None:
    global _current
    _current = code if code in _LANG_INDEX else "ua"


def get_lang() -> str:
    return _current


def keys() -> list[str]:
    _ensure_worlds()
    return list(_S)


def has(key: str) -> bool:
    _ensure_worlds()
    return key in _S


def raw(key: str) -> tuple[str, str, str]:
    _ensure_worlds()
    return _S[key]


def t(key: str, lang: str | None = None, **fmt: object) -> str:
    """Translate ``key``; missing keys fall back to the key itself."""
    _ensure_worlds()
    entry = _S.get(key)
    if entry is None:
        return key
    text = entry[_LANG_INDEX.get(lang or _current, 0)]
    return text.format(**fmt) if fmt else text
