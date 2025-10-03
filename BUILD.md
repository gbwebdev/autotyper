# Building Standalone Binaries

This document explains how to build standalone Linux binaries for autotyper.

## Prerequisites

### System Requirements
- Linux system (Ubuntu/Debian recommended)
- Python 3.8 or higher
- Build tools: `build-essential`, `python3-dev`
- Optional: `upx-ucl` for binary compression

### Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
  python3-dev \
  libffi-dev \
  libssl-dev \
  build-essential \
  upx-ucl

# Or install UPX separately
sudo apt-get install upx-ucl
```

## Building Locally

### Method 1: Using the Build Script (Recommended)

```bash
# Build binary
./build-binary.sh

# Clean build (removes previous builds)
./build-binary.sh clean
```

### Method 2: Using Make

```bash
# Build binary
make binary

# Clean build
make binary-clean

# Test built binary
make binary-test
```

### Method 3: Manual PyInstaller

```bash
# Install dependencies
pip install -e ".[build]"

# Build binary
pyinstaller --clean autotyper.spec

# Test binary
./dist/autotyper --help
```

## GitHub Actions Workflow

The project includes automated binary building via GitHub Actions:

### Triggers
- **Tags**: Creates releases with binaries (e.g., `v1.0.0`)
- **Pull Requests**: Tests build process
- **Manual**: Can be triggered manually via GitHub UI

### Workflow Features
- Builds on Ubuntu latest
- Tests the binary after building
- Uploads binary as artifact
- Creates GitHub releases on tags
- Includes comprehensive release notes

### Using the Workflow

1. **Create a Release**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Manual Trigger**:
   - Go to Actions tab in GitHub
   - Select "Build Linux Binary" workflow
   - Click "Run workflow"

3. **Download Binary**:
   - Go to the latest release
   - Download the `autotyper` binary
   - Make executable: `chmod +x autotyper`

## Binary Features

### What's Included
- Complete autotyper functionality
- All keyboard layouts (US, French AZERTY, OVH KVM)
- Multiple backends (uinput, pyautogui)
- Unicode fallback support
- All dependencies bundled

### Binary Size
- **Without UPX**: ~15-20 MB
- **With UPX**: ~5-8 MB (compressed)

### Compatibility
- **Target**: Linux x86_64
- **Dependencies**: Self-contained (no Python required)
- **Backends**: uinput (Linux), pyautogui (fallback)

## Installation

### System-wide Installation
```bash
# Download binary
wget https://github.com/guillaume-biton/autotyper/releases/latest/download/autotyper

# Make executable
chmod +x autotyper

# Install system-wide
sudo cp autotyper /usr/local/bin/

# Test installation
autotyper --help
```

### Local Installation
```bash
# Download and run directly
wget https://github.com/guillaume-biton/autotyper/releases/latest/download/autotyper
chmod +x autotyper
./autotyper --help
```

## Troubleshooting

### Common Issues

1. **Permission Denied on /dev/uinput**:
   ```bash
   # Add user to input group
   sudo usermod -a -G input $USER
   # Log out and back in
   ```

2. **Binary Not Found**:
   ```bash
   # Check if binary exists
   ls -la dist/autotyper
   
   # Check build logs
   ./build-binary.sh clean
   ```

3. **Import Errors**:
   ```bash
   # Ensure all dependencies are installed
   pip install -e ".[build]"
   
   # Check Python path
   python -c "import sys; print(sys.path)"
   ```

### Debug Mode

```bash
# Build with debug info
pyinstaller --debug=all autotyper.spec

# Test with verbose output
./dist/autotyper --help --verbose
```

## Development

### Modifying the Build

1. **Update Dependencies**: Edit `pyproject.toml`
2. **Modify Spec File**: Edit `autotyper.spec`
3. **Update Workflow**: Edit `.github/workflows/build-binary.yml`

### Testing Changes

```bash
# Test locally
make binary-test

# Test in CI
git push origin feature-branch
# Check GitHub Actions
```

## Release Process

1. **Update Version**: Edit `pyproject.toml` and `src/autotyper/__init__.py`
2. **Create Tag**: `git tag v1.0.0`
3. **Push Tag**: `git push origin v1.0.0`
4. **Verify Release**: Check GitHub releases page
5. **Test Binary**: Download and test the released binary

## Security Notes

- Binaries are built in clean GitHub Actions environment
- All dependencies are pinned to specific versions
- Binary includes only necessary code (excludes dev tools)
- UPX compression is optional and reversible
