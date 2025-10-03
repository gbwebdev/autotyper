#!/usr/bin/env python3
"""
CLI entry point for autotyper.
"""

import argparse
import getpass
import platform
import sys
import time
from typing import Optional, Set

from .core import (
    LAYOUTS,
    infer_default_layout,
    parse_override_json,
    backend_uinput,
    backend_osascript,
    backend_pyautogui,
)


def main() -> None:
    """Main CLI entry point."""
    ap = argparse.ArgumentParser(
        description="Type a password into the focused window (uinput, layout-aware)."
    )
    ap.add_argument(
        "-w", "--wait", type=float, default=5.0, help="Seconds to wait before typing (default: 5)."
    )
    ap.add_argument("-e", "--enter", action="store_true", help="Press Enter after typing.")
    ap.add_argument(
        "-r", "--rate", type=float, default=0.06, help="Seconds between keystrokes (default: 0.06)."
    )
    ap.add_argument(
        "--backend",
        choices=["auto", "uinput", "pyautogui", "osascript"],
        default="auto",
        help="auto: Linux=uinput, macOS=osascript, else=pyautogui.",
    )
    ap.add_argument(
        "--layout",
        choices=list(LAYOUTS.keys()) + ["auto"],
        default="auto",
        help="Keyboard layout (default: auto-detect).",
    )
    ap.add_argument(
        "--show-unsupported",
        action="store_true",
        help="List unsupported chars pre-fallback.",
    )
    ap.add_argument(
        "--dump-layout",
        action="store_true",
        help="Print resolved mapping and exit.",
    )
    # priming
    try:
        from argparse import BooleanOptionalAction

        bool_action = BooleanOptionalAction
    except Exception:
        bool_action = "store_true"
    ap.add_argument(
        "--prime",
        action=bool_action,
        default=True,
        help="Prime virtual keyboard to avoid dropping first char (default: true).",
    )
    ap.add_argument(
        "--prime-delay",
        type=float,
        default=0.25,
        help="Seconds to wait before/after priming (default: 0.25).",
    )
    # overrides
    ap.add_argument(
        "--override",
        type=str,
        default=None,
        help='JSON overrides: e.g. \'{"{":"KEY_8+altgr+shift"}\'',
    )
    # unicode fallback controls
    ap.add_argument(
        "--unicode-fallback",
        action=bool_action,
        default=True,
        help="Enable Ctrl+Shift+U hex fallback (default: true).",
    )
    ap.add_argument(
        "--unicode-only",
        type=str,
        default=None,
        help="Force Unicode fallback for ONLY these characters.",
    )
    ap.add_argument(
        "--unicode-except",
        type=str,
        default=None,
        help="Remove these from the default Unicode-preferred set.",
    )
    # numpad control (ignored for layout=ovh; ovh always uses keypad digits)
    ap.add_argument(
        "--numpad",
        dest="numpad",
        action=bool_action,
        default=True,
        help="Use keypad keys for digits 0–9 (default: true; always on for --layout ovh).",
    )

    args = ap.parse_args()

    # backend
    if args.backend == "auto":
        sysname = platform.system().lower()
        backend = "uinput" if sysname == "linux" else ("osascript" if sysname == "darwin" else "pyautogui")
    else:
        backend = args.backend

    # layout
    layout = infer_default_layout() if args.layout == "auto" else args.layout

    # overrides
    overrides = None
    if args.override:
        try:
            overrides = parse_override_json(args.override)
        except Exception as ex:
            print("Invalid --override JSON:", ex)
            sys.exit(2)

    # secure prompt
    try:
        secret = getpass.getpass("Password (hidden): ")
    except Exception:
        print("Failed to read password securely.")
        sys.exit(1)
    if not secret:
        print("Empty password, aborting.")
        sys.exit(1)

    print(f"Focus the target window. Typing starts in {args.wait} seconds...")
    try:
        time.sleep(args.wait)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)

    unicode_only: Optional[Set[str]] = set(args.unicode_only) if args.unicode_only else None
    unicode_except: Optional[Set[str]] = set(args.unicode_except) if args.unicode_except else None

    if backend == "uinput":
        ok, err = backend_uinput(
            secret,
            args.rate,
            args.enter,
            layout,
            args.show_unsupported,
            args.prime,
            args.prime_delay,
            overrides=overrides,
            dump_layout=args.dump_layout,
            unicode_fallback=args.unicode_fallback,
            unicode_only=unicode_only,
            unicode_except=unicode_except,
            use_numpad_flag=args.numpad,
        )
    elif backend == "osascript":
        ok, err = backend_osascript(secret, args.rate, args.enter)
    elif backend == "pyautogui":
        ok, err = backend_pyautogui(secret, args.rate, args.enter)
    else:
        ok, err = False, f"Unknown backend: {backend}"

    if args.dump_layout:
        sys.exit(0)

    if ok:
        numpad_info = ", digits=numpad" if layout == "ovh" or args.numpad else ", digits=top-row"
        print(f"Done via {backend} (layout={layout}{numpad_info}).")
    else:
        print("Failed to send keystrokes.")
        if err:
            print("Reason:", err)
            sys.exit(2)


if __name__ == "__main__":
    main()
