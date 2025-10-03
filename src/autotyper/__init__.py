"""
autotyper - Layout-aware, Wayland-friendly password typer.

A small tool to mimic keyboard typing from given input (for when you cannot paste).
Supports multiple backends (uinput, osascript, pyautogui) and keyboard layouts.
"""

__version__ = "1.0.0"
__author__ = "Guillaume Biton"
__email__ = "guillaume.biton@example.com"

from .core import (
    LAYOUTS,
    autodetect_layout_linux,
    infer_default_layout,
    parse_override_json,
    backend_uinput,
    backend_osascript,
    backend_pyautogui,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "LAYOUTS",
    "autodetect_layout_linux",
    "infer_default_layout",
    "parse_override_json",
    "backend_uinput",
    "backend_osascript",
    "backend_pyautogui",
]
