#!/usr/bin/env python3
"""
autotyper.py — layout-aware, Wayland-friendly (uinput) password typer.

New in this build:
- Layout `ovh`: letters = AZERTY, symbols = US/QWERTY, digits = keypad (KP0..KP9)
- `ovh` ignores --no-numpad (digits always typed via keypad)

Also includes:
- Linux default backend: uinput (Wayland-friendly)
- macOS fallback: osascript (Accessibility permission required)
- Optional pyautogui fallback (X11)
- Built-in layouts: us, en-in (alias of us), fr-azerty (classic), ovh
- FR fixes: correct , . / : ; ? and adds ~ ° ²
- Auto layout detection (Linux): gsettings/localectl → LANG → default
- AltGr support (+ Shift) when used
- Priming step so the first char isn’t swallowed
- Unicode fallback (Ctrl+Shift+U hex Space), tuned for FR (off for ?!+*)
- Overrides and layout dumping for diagnostics
"""

import argparse
import getpass
import json
import os
import platform
import subprocess
import sys
import time
from typing import Dict, Tuple, Optional, Union, List, Set

MappingEntry = Union[Tuple[str, bool], Tuple[str, bool, bool]]  # (KEY_NAME, shift[, altgr])
K = lambda name: name

# ----------------- Base layouts -----------------

def make_us_layout() -> Dict[str, MappingEntry]:
    L: Dict[str, MappingEntry] = {}
    # letters
    for ch in "abcdefghijklmnopqrstuvwxyz":
        L[ch] = (f"KEY_{ch.upper()}", False)
        L[ch.upper()] = (f"KEY_{ch.upper()}", True)
    # digits row + shifted symbols
    DIG = ")!@#$%^&*("
    for i, ch in enumerate("1234567890"):
        L[ch] = (f"KEY_{ch}", False)
        L[DIG[i]] = (f"KEY_{'0' if ch=='0' else ch}", True)
    # whitespace / control
    L[" "] = (K("KEY_SPACE"), False)
    L["\t"] = (K("KEY_TAB"), False)
    L["\n"] = (K("KEY_ENTER"), False)
    # punctuation
    L["-"] = (K("KEY_MINUS"), False); L["_"] = (K("KEY_MINUS"), True)
    L["="] = (K("KEY_EQUAL"), False); L["+"] = (K("KEY_EQUAL"), True)
    L["["] = (K("KEY_LEFTBRACE"), False); L["{"] = (K("KEY_LEFTBRACE"), True)
    L["]"] = (K("KEY_RIGHTBRACE"), False); L["}"] = (K("KEY_RIGHTBRACE"), True)
    L["\\"] = (K("KEY_BACKSLASH"), False); L["|"] = (K("KEY_BACKSLASH"), True)
    L[";"] = (K("KEY_SEMICOLON"), False); L[":"] = (K("KEY_SEMICOLON"), True)
    L["'"] = (K("KEY_APOSTROPHE"), False); L['"'] = (K("KEY_APOSTROPHE"), True)
    L[","] = (K("KEY_COMMA"), False); L["<"] = (K("KEY_COMMA"), True)
    L["."] = (K("KEY_DOT"), False); L[">"] = (K("KEY_DOT"), True)
    L["/"] = (K("KEY_SLASH"), False); L["?"] = (K("KEY_SLASH"), True)
    L["`"] = (K("KEY_GRAVE"), False); L["~"] = (K("KEY_GRAVE"), True)
    return L

def make_fr_azerty_layout() -> Dict[str, MappingEntry]:
    """
    French AZERTY (classic):
      • Digits 1..0 require Shift; unshifted top row: & é " ' ( - è _ ç à
      • US KEY_MINUS → ')' (no shift), Shift → '°'
      • '²' at KEY_GRAVE (above Tab) (no shift)
      • '?' = Shift+M ; and fix , . / : ; ? block
      • '~' via AltGr+2
    """
    L: Dict[str, MappingEntry] = {}
    # letters (physical FR)
    L["a"] = (K("KEY_Q"), False); L["z"] = (K("KEY_W"), False); L["e"] = (K("KEY_E"), False)
    L["r"] = (K("KEY_R"), False); L["t"] = (K("KEY_T"), False); L["y"] = (K("KEY_Y"), False)
    L["u"] = (K("KEY_U"), False); L["i"] = (K("KEY_I"), False); L["o"] = (K("KEY_O"), False)
    L["p"] = (K("KEY_P"), False)
    L["q"] = (K("KEY_A"), False); L["s"] = (K("KEY_S"), False); L["d"] = (K("KEY_D"), False)
    L["f"] = (K("KEY_F"), False); L["g"] = (K("KEY_G"), False); L["h"] = (K("KEY_H"), False)
    L["j"] = (K("KEY_J"), False); L["k"] = (K("KEY_K"), False); L["l"] = (K("KEY_L"), False)
    L["m"] = (K("KEY_SEMICOLON"), False)
    L["w"] = (K("KEY_Z"), False); L["x"] = (K("KEY_X"), False); L["c"] = (K("KEY_C"), False)
    L["v"] = (K("KEY_V"), False); L["b"] = (K("KEY_B"), False); L["n"] = (K("KEY_N"), False)
    for ch in "abcdefghijklmnopqrstuvwxyz":
        if ch in L:
            key, _ = L[ch]; L[ch.upper()] = (key, True)

    # digits need Shift
    for ch in "1234567890":
        L[ch] = (f"KEY_{ch}", True)

    # top unshifted symbols: & é " ' ( - è _ ç à
    top_unshift = ['&','é','"',"'",'(','-','è','_','ç','à']
    for idx, sym in enumerate(top_unshift, start=1):
        keyname = "KEY_0" if idx == 10 else f"KEY_{idx}"
        L[sym] = (keyname, False)

    # space/control
    L[" "] = (K("KEY_SPACE"), False); L["\t"] = (K("KEY_TAB"), False); L["\n"] = (K("KEY_ENTER"), False)

    # specifics
    L["-"] = (K("KEY_6"), False); L["_"] = (K("KEY_8"), False)
    L[")"] = (K("KEY_MINUS"), False); L["°"] = (K("KEY_MINUS"), True)
    L["²"] = (K("KEY_GRAVE"), False)
    L["~"] = ("KEY_2", False, True)  # AltGr+2

    # punctuation block (classic FR)
    L[","] = (K("KEY_SEMICOLON"), False)
    L["?"] = (K("KEY_SEMICOLON"), True)
    L[";"] = (K("KEY_COMMA"), False)
    L["."] = (K("KEY_COMMA"), True)
    L[":"] = (K("KEY_DOT"), False)
    L["/"] = (K("KEY_DOT"), True)

    # dev symbols (may vary)
    L["["] = ("KEY_8", False, True);  L["{"] = ("KEY_8", True,  True)
    L["]"] = ("KEY_9", False, True);  L["}"] = ("KEY_9", True,  True)
    L["|"] = ("KEY_6", False, True);  L["\\"] = ("KEY_8", False, True)
    L["#"] = ("KEY_3", False, True);  L["@"] = ("KEY_0", False, True)

    # dedicated keys (no Unicode)
    L["+"] = (K("KEY_EQUAL"), True); L["*"] = (K("KEY_BACKSLASH"), False); L["!"] = (K("KEY_SLASH"), False)
    return L

# ----------------- OVH layout -----------------

def make_ovh_layout() -> Dict[str, MappingEntry]:
    """
    OVH KVM quirk layout:
      - Letters = AZERTY (French physical positions)
      - Symbols = US/QWERTY, with extra OVH-specific adjustments below
      - Digits = keypad only (KP0..KP9), and also KP '/' and KP '-'
    """
    us = make_us_layout()
    L: Dict[str, MappingEntry] = dict(us)  # start from US symbols

    # ----- Letters: AZERTY physical positions -----
    fr_letters = {
        "a":"KEY_Q","z":"KEY_W","e":"KEY_E","r":"KEY_R","t":"KEY_T","y":"KEY_Y",
        "u":"KEY_U","i":"KEY_I","o":"KEY_O","p":"KEY_P",
        "q":"KEY_A","s":"KEY_S","d":"KEY_D","f":"KEY_F","g":"KEY_G","h":"KEY_H",
        "j":"KEY_J","k":"KEY_K","l":"KEY_L","m":"KEY_SEMICOLON",
        "w":"KEY_Z","x":"KEY_X","c":"KEY_C","v":"KEY_V","b":"KEY_B","n":"KEY_N",
    }
    for ch, keyname in fr_letters.items():
        L[ch] = (keyname, False)
        L[ch.upper()] = (keyname, True)

    # ----- Digits & arithmetic: force keypad -----
    kp = ["KEY_KP0","KEY_KP1","KEY_KP2","KEY_KP3","KEY_KP4",
          "KEY_KP5","KEY_KP6","KEY_KP7","KEY_KP8","KEY_KP9"]
    for d, keyname in zip("0123456789", kp):
        L[d] = (keyname, False)

    # Also send slash and minus from keypad (per OVH)
    L["/"] = ("KEY_KPSLASH", False)
    L["-"] = ("KEY_KPMINUS", False)

    # ----- OVH-specific symbol quirks -----
    # '>' acts like FR '.'  → Shift + COMMA
    L[">"] = ("KEY_COMMA", True)
    # '<' acts like FR '?'  → Shift + M (evdev KEY_SEMICOLON)
    L["<"] = ("KEY_SEMICOLON", True)
    # '.' acts like FR ';'  → COMMA (no shift)
    L["."] = ("KEY_COMMA", False)
    # '|' is Shift + the <> key next to Left Shift (evdev KEY_102ND)
    L["|"] = ("KEY_102ND", True)
    # underscore (not on keypad): use US underscore
    L["_"] = ("KEY_MINUS", True)

    return L


LAYOUTS: Dict[str, Dict[str, MappingEntry]] = {
    "us": make_us_layout(),
    "en-in": make_us_layout(),
    "fr-azerty": make_fr_azerty_layout(),
    "ovh": make_ovh_layout(),
}

# -------- Auto-detect layout (Linux) --------

def autodetect_layout_linux() -> Optional[str]:
    try:
        out = subprocess.check_output(
            ["gsettings", "get", "org.gnome.desktop.input-sources", "sources"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        if out:
            if "'fr'" in out: return "fr-azerty"
            if "'us'" in out: return "us"
            if "'in'" in out: return "en-in"
    except Exception:
        pass
    try:
        out = subprocess.check_output(["localectl", "status"], stderr=subprocess.DEVNULL, text=True).lower()
        if "x11 layout" in out or "keyboard layout" in out:
            if " fr" in out: return "fr-azerty"
            if " us" in out: return "us"
            if " english (india)" in out or "\nin" in out: return "en-in"
    except Exception:
        pass
    return None

def infer_default_layout() -> str:
    if platform.system().lower() == "linux":
        auto = autodetect_layout_linux()
        if auto: return auto
    lang = os.environ.get("LANG","").lower()
    if lang.startswith("fr"): return "fr-azerty"
    if lang.startswith("en_in") or lang.startswith("en-in"): return "en-in"
    return "us"

# -------- Overrides --------

def parse_override_json(s: str) -> Dict[str, MappingEntry]:
    obj = json.loads(s)
    out: Dict[str, MappingEntry] = {}
    for ch, val in obj.items():
        if not isinstance(ch, str) or len(ch) != 1:
            raise ValueError("override keys must be single characters")
        if isinstance(val, str):
            parts = val.split("+")
            key = parts[0]
            need_shift = any(p.lower()=="shift" for p in parts[1:])
            need_altgr = any(p.lower()=="altgr" for p in parts[1:])
            out[ch] = (key, need_shift, need_altgr)
        elif isinstance(val, dict):
            key = val["key"]; need_shift = bool(val.get("shift", False)); need_altgr = bool(val.get("altgr", False))
            out[ch] = (key, need_shift, need_altgr)
        else:
            raise ValueError("override values must be string or object")
    return out

# -------- Backends --------

def backend_osascript(text: str, rate: float, press_enter: bool):
    if platform.system().lower() != "darwin":
        return False, "osascript backend only for macOS"
    p = subprocess.run(["osascript","-e",f'tell application "System Events" to keystroke {text!r}'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        return False, p.stderr.decode() or "osascript failed"
    if press_enter:
        p = subprocess.run(["osascript","-e",'tell application "System Events" to key code 36'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            return False, p.stderr.decode() or "osascript enter failed"
    return True, None

def backend_pyautogui(text: str, rate: float, press_enter: bool):
    try:
        import pyautogui
    except Exception as e:
        return False, f"pyautogui not available: {e}"
    try:
        pyautogui.write(text, interval=rate)
        if press_enter: pyautogui.press("enter")
        return True, None
    except Exception as e:
        return False, f"pyautogui failed: {e}"

# -------- Linux uinput with Unicode fallback + Numpad --------

def backend_uinput(text: str, rate: float, press_enter: bool,
                   layout_name: str, show_unsupported: bool,
                   prime: bool, prime_delay: float,
                   overrides: Optional[Dict[str, MappingEntry]] = None,
                   dump_layout: bool = False,
                   unicode_fallback: bool = True,
                   unicode_only: Optional[Set[str]] = None,
                   unicode_except: Optional[Set[str]] = None,
                   use_numpad_flag: bool = True):
    if platform.system().lower() != "linux":
        return False, "uinput backend only on Linux"
    if not os.path.exists("/dev/uinput"):
        return False, "/dev/uinput is missing (load uinput module)"
    if not os.access("/dev/uinput", os.W_OK):
        return False, "No write access to /dev/uinput (udev rule + input group, or run with sudo)"
    try:
        from evdev import UInput, ecodes as e
    except Exception as ex:
        return False, f"python-evdev not available: {ex}"

    mapping = dict(LAYOUTS.get(layout_name, {}))
    if not mapping:
        return False, f"Unknown layout: {layout_name}"
    if overrides:
        mapping.update(overrides)

    # FR: prefer Unicode for tricky dev symbols — NOT for ?!+*
    default_unicode_prefer: Set[str] = set()
    if layout_name == "fr-azerty":
        default_unicode_prefer = set("`{}[]|\\^@")

    # `ovh` uses US symbols; no special unicode-prefer set needed
    if unicode_only is not None:
        unicode_prefer = set(unicode_only)
    else:
        unicode_prefer = set(default_unicode_prefer)
        if unicode_except:
            unicode_prefer = {c for c in unicode_prefer if c not in unicode_except}

    # Resolve keyname -> code
    name_to_code = {name: getattr(e, name) for name in dir(e) if name.startswith("KEY_")}

    # If `ovh`, digits are already mapped to KP in layout; ignore --no-numpad
    if layout_name != "ovh":
        if use_numpad_flag:
            for d, keyname in zip("0123456789",
                                  ["KEY_KP0","KEY_KP1","KEY_KP2","KEY_KP3","KEY_KP4",
                                   "KEY_KP5","KEY_KP6","KEY_KP7","KEY_KP8","KEY_KP9"]):
                mapping[d] = (keyname, False)
        # else: leave digits as the layout defined

    # Build resolved mapping
    resolved: Dict[str, List[Tuple[int,bool,bool]]] = {}
    def add_step(lst, key_name: str, need_shift=False, need_altgr=False):
        code = name_to_code.get(key_name)
        if code is None: return False
        lst.append((code, need_shift, need_altgr)); return True

    for ch, ent in mapping.items():
        if len(ent) == 2:
            key_name, need_shift = ent  # type: ignore
            need_altgr = False
        else:
            key_name, need_shift, need_altgr = ent  # type: ignore
        code = name_to_code.get(key_name)
        if code is not None:
            resolved.setdefault(ch, []).append((code, need_shift, need_altgr))

    # pre-fallback unsupported
    unsupported = [c for c in set(text) if c != "\n" and c not in resolved and not unicode_fallback]
    if show_unsupported and unsupported:
        print("Warning: unsupported chars (pre-fallback) will be skipped:", "".join(sorted(unsupported)))

    if dump_layout:
        print("=== Effective mapping (first step per char) ===")
        for ch in sorted(resolved.keys(), key=lambda x: ord(x)):
            code, sh, ag = resolved[ch][0]
            print(repr(ch), "->", code, f"shift={sh}", f"altgr={ag}")
        return True, None

    # supported key set
    supported_codes = {code for steps in resolved.values() for (code,_,_) in steps}
    supported_codes.update([e.KEY_LEFTSHIFT, e.KEY_RIGHTALT, e.KEY_LEFTCTRL, e.KEY_ENTER, e.KEY_SPACE, e.KEY_TAB, e.KEY_U])

    def press(ui, code: int, down: bool):
        ui.write(e.EV_KEY, code, 1 if down else 0)
        ui.write(e.EV_SYN, e.SYN_REPORT, 0)

    def tap(ui, code: int):
        press(ui, code, True); press(ui, code, False)

    def type_char_steps(ui, ch: str, delay: float):
        steps = resolved.get(ch)
        if not steps: return False
        for (code, need_shift, need_altgr) in steps:
            if need_altgr: press(ui, e.KEY_RIGHTALT, True)
            if need_shift: press(ui, e.KEY_LEFTSHIFT, True)
            tap(ui, code)
            if need_shift: press(ui, e.KEY_LEFTSHIFT, False)
            if need_altgr: press(ui, e.KEY_RIGHTALT, False)
            time.sleep(max(0.0, delay/2))
        time.sleep(delay)
        return True

    # Unicode fallback: Ctrl+Shift+U hex Space
    def unicode_type(ui, ch: str, delay: float) -> bool:
        codepoint = ord(ch)
        hexstr = f"{codepoint:x}"
        press(ui, e.KEY_LEFTCTRL, True); press(ui, e.KEY_LEFTSHIFT, True); tap(ui, e.KEY_U)
        press(ui, e.KEY_LEFTSHIFT, False); press(ui, e.KEY_LEFTCTRL, False)
        time.sleep(max(0.05, delay))
        for hd in hexstr:
            ok = type_char_steps(ui, hd, delay/2 if delay > 0 else 0.0)
            if not ok:
                keyname = f"KEY_{hd.upper()}"
                if keyname in name_to_code:
                    tap(ui, name_to_code[keyname])
                else:
                    return False
        tap(ui, e.KEY_SPACE)
        time.sleep(delay)
        return True

    try:
        with UInput(name=f"autotyper-virtual-kbd-{layout_name}",
                    events={e.EV_KEY: list(supported_codes)}) as ui:
            time.sleep(prime_delay)
            if prime:
                tap(ui, e.KEY_LEFTSHIFT)
                time.sleep(prime_delay)

            for ch in text:
                if ch == "\n":
                    tap(ui, e.KEY_ENTER); time.sleep(rate); continue

                # For `ovh`, we rely on mapping (US symbols + FR letters). Unicode only if unmapped.
                use_unicode = unicode_fallback and (ch not in resolved)

                sent = unicode_type(ui, ch, rate) if use_unicode else type_char_steps(ui, ch, rate)
                if not sent and unicode_fallback and not use_unicode:
                    sent = unicode_type(ui, ch, rate)
                # else drop silently

            if press_enter:
                tap(ui, e.KEY_ENTER)
        return True, None
    except PermissionError:
        return False, "Permission denied on /dev/uinput"
    except Exception as ex:
        return False, f"uinput typing failed: {ex}"

# ----------------- CLI -----------------

def main():
    ap = argparse.ArgumentParser(description="Type a password into the focused window (uinput, layout-aware).")
    ap.add_argument("-w","--wait", type=float, default=5.0, help="Seconds to wait before typing (default: 5).")
    ap.add_argument("-e","--enter", action="store_true", help="Press Enter after typing.")
    ap.add_argument("-r","--rate", type=float, default=0.06, help="Seconds between keystrokes (default: 0.06).")
    ap.add_argument("--backend", choices=["auto","uinput","pyautogui","osascript"], default="auto",
                    help="auto: Linux=uinput, macOS=osascript, else=pyautogui.")
    ap.add_argument("--layout", choices=list(LAYOUTS.keys())+["auto"], default="auto",
                    help="Keyboard layout (default: auto-detect).")
    ap.add_argument("--show-unsupported", action="store_true",
                    help="List unsupported chars pre-fallback.")
    ap.add_argument("--dump-layout", action="store_true",
                    help="Print resolved mapping and exit.")
    # priming
    try:
        from argparse import BooleanOptionalAction
        bool_action = BooleanOptionalAction
    except Exception:
        bool_action = "store_true"
    ap.add_argument("--prime", action=bool_action, default=True,
                    help="Prime virtual keyboard to avoid dropping first char (default: true).")
    ap.add_argument("--prime-delay", type=float, default=0.25,
                    help="Seconds to wait before/after priming (default: 0.25).")
    # overrides
    ap.add_argument("--override", type=str, default=None,
                    help='JSON overrides: e.g. \'{"{":"KEY_8+altgr+shift"}\'')
    # unicode fallback controls
    ap.add_argument("--unicode-fallback", action=bool_action, default=True,
                    help="Enable Ctrl+Shift+U hex fallback (default: true).")
    ap.add_argument("--unicode-only", type=str, default=None,
                    help="Force Unicode fallback for ONLY these characters.")
    ap.add_argument("--unicode-except", type=str, default=None,
                    help="Remove these from the default Unicode-preferred set.")
    # numpad control (ignored for layout=ovh; ovh always uses keypad digits)
    ap.add_argument("--numpad", dest="numpad", action=bool_action, default=True,
                    help="Use keypad keys for digits 0–9 (default: true; always on for --layout ovh).")

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
            print("Invalid --override JSON:", ex); sys.exit(2)

    # secure prompt
    try:
        secret = getpass.getpass("Password (hidden): ")
    except Exception:
        print("Failed to read password securely."); sys.exit(1)
    if not secret:
        print("Empty password, aborting."); sys.exit(1)

    print(f"Focus the target window. Typing starts in {args.wait} seconds...")
    try:
        time.sleep(args.wait)
    except KeyboardInterrupt:
        print("\nCancelled."); sys.exit(0)

    if backend == "uinput":
        ok, err = backend_uinput(
            secret, args.rate, args.enter, layout,
            args.show_unsupported, args.prime, args.prime_delay,
            overrides=overrides, dump_layout=args.dump_layout,
            unicode_fallback=args.unicode_fallback,
            unicode_only=set(args.unicode_only) if args.unicode_only else None,
            unicode_except=set(args.unicode_except) if args.unicode_except else None,
            use_numpad_flag=args.numpad
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
        print(f"Done via {backend} (layout={layout}{', digits=numpad' if layout=='ovh' or args.numpad else ', digits=top-row'}).")
    else:
        print("Failed to send keystrokes.")
        if err: print("Reason:", err); sys.exit(2)

if __name__ == "__main__":
    main()
