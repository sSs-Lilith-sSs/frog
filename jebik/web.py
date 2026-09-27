"""Browser-only helpers (pygbag build): save storage and text entry.

* pygbag's file system lives in memory and is gone after a page reload, so on
  the web :mod:`jebik.save` stores its JSON text under one ``localStorage`` key
  (kept by Safari / Chrome per site and device). Keep that text ASCII
  (``json.dumps`` default): non-ASCII strings sent to JavaScript get mangled.
* Phones show no keyboard for SDL text input in the browser, so a tap on a text
  field asks with the page's own ``prompt()`` dialog (:func:`ask_text`).

Only called when :func:`jebik.paths.is_web` is true — desktop never touches
``platform.window``; every call degrades quietly on failure.
"""
from __future__ import annotations

import json

KEY = "jebik.save"


def _window():
    import platform  # pygbag replaces the stdlib module with its browser bridge
    return platform.window


def _storage():
    return _window().localStorage


def read(key: str = KEY) -> str | None:
    try:
        value = _storage().getItem(key)
    except Exception:           # no bridge / storage disabled (private mode)
        return None
    return value if isinstance(value, str) else None


def write(text: str, key: str = KEY) -> bool:
    try:
        _storage().setItem(key, text)
        return True
    except Exception:
        return False


def remove(key: str = KEY) -> None:
    try:
        _storage().removeItem(key)
    except Exception:
        pass


def ask_text(message: str, default: str = "") -> str | None:
    """The browser's text prompt (shows the phone keyboard); None if cancelled.
    Strings going *to* JavaScript lose non-ASCII text in pygbag's bridge, so the
    call is sent as ASCII source with ``\\u`` escapes."""
    try:
        value = _window().eval(f"prompt({json.dumps(message)}, {json.dumps(default)})")
    except Exception:
        return None
    return value if isinstance(value, str) else None
