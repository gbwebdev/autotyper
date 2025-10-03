# autotyper

A layout-aware, Wayland-friendly password typer with multiple backends.

## Features

- **Multiple backends**: uinput (Linux), osascript (macOS), pyautogui (fallback)
- **Layout support**: US, French AZERTY, OVH KVM, and auto-detection
- **Wayland-friendly**: Uses uinput on Linux for better compatibility
- **Unicode fallback**: Ctrl+Shift+U hex input for unsupported characters
- **Security**: Secure password input with hidden prompts
- **Flexible**: JSON overrides for custom key mappings

## Installation

### Standalone Binary (Recommended for Linux)

Download the pre-built binary from the [latest release](https://github.com/guillaume-biton/autotyper/releases/latest):

```bash
# Download and install
wget https://github.com/guillaume-biton/autotyper/releases/latest/download/autotyper
chmod +x autotyper
sudo cp autotyper /usr/local/bin/
```

### From PyPI

```bash
pip install autotyper
```

### From source

```bash
git clone https://github.com/guillaume-biton/autotyper.git
cd autotyper
pip install -e .
```

### Development installation

```bash
git clone https://github.com/guillaume-biton/autotyper.git
cd autotyper
pip install -e ".[dev]"
```

## Requirements

### Linux
- `python-evdev` (automatically installed)
- Write access to `/dev/uinput` (requires udev rules or sudo)

### macOS
- No additional dependencies (uses built-in osascript)

### Other systems
- `pyautogui` (automatically installed as fallback)

## Usage

### Basic usage

```bash
autotyper
```

This will:
1. Prompt for a password (hidden input)
2. Wait 5 seconds for you to focus the target window
3. Type the password using the detected keyboard layout

### Command line options

```bash
autotyper --help
```

Key options:
- `-w, --wait SECONDS`: Wait time before typing (default: 5)
- `-e, --enter`: Press Enter after typing
- `-r, --rate SECONDS`: Delay between keystrokes (default: 0.06)
- `--layout LAYOUT`: Force specific layout (us, fr-azerty, ovh, auto)
- `--backend BACKEND`: Force specific backend (uinput, osascript, pyautogui, auto)
- `--dump-layout`: Show key mappings and exit
- `--override JSON`: Custom key overrides

### Examples

```bash
# Type with Enter key
autotyper --enter

# Use French AZERTY layout
autotyper --layout fr-azerty

# Custom timing
autotyper --wait 3 --rate 0.1

# Show key mappings
autotyper --dump-layout --layout fr-azerty

# Custom key override
autotyper --override '{"{":"KEY_8+altgr+shift"}'
```

## Supported Layouts

- `us`: US QWERTY (default)
- `fr-azerty`: French AZERTY
- `ovh`: OVH KVM layout (AZERTY letters, US symbols, keypad digits)
- `en-in`: English India (alias for US)
- `auto`: Auto-detect from system settings

## Backends

- **uinput** (Linux): Direct kernel input events, Wayland-compatible
- **osascript** (macOS): Uses AppleScript for typing
- **pyautogui** (fallback): Cross-platform but may not work in all environments

## Development

### Setup

```bash
git clone https://github.com/guillaume-biton/autotyper.git
cd autotyper
pip install -e ".[dev]"
```

### Running tests

```bash
pytest
```

### Code formatting

```bash
black src/ tests/
isort src/ tests/
```

### Type checking

```bash
mypy src/
```

### Building binaries

```bash
# Build standalone binary
make binary

# Or use the build script
./build-binary.sh

# Test the binary
make binary-test
```

See [BUILD.md](BUILD.md) for detailed build instructions.

## License

MIT License - see LICENSE file for details.
