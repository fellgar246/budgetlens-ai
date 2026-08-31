from __future__ import annotations

_shutting_down = False


def mark_shutting_down() -> None:
    global _shutting_down
    _shutting_down = True


def is_shutting_down() -> bool:
    return _shutting_down


def reset_runtime() -> None:
    global _shutting_down
    _shutting_down = False
