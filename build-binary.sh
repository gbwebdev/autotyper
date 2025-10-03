#!/bin/bash
set -e

# Build script for creating standalone Linux binary
# Usage: ./build-binary.sh [clean]

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"

echo "🔨 Building autotyper Linux binary..."

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Not in a virtual environment. Consider using one for cleaner builds."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Clean previous builds if requested
if [[ "$1" == "clean" ]]; then
    echo "🧹 Cleaning previous builds..."
    rm -rf "$BUILD_DIR" "$DIST_DIR" "*.egg-info"
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
fi

# Install/upgrade build dependencies
echo "📦 Installing build dependencies..."
pip install --upgrade pip
pip install -e ".[build]"

# Check if UPX is available for compression
if command -v upx >/dev/null 2>&1; then
    echo "✅ UPX found - will compress binary"
    UPX_AVAILABLE=true
else
    echo "⚠️  UPX not found - binary will be larger (install with: apt install upx-ucl)"
    UPX_AVAILABLE=false
fi

# Build the binary
echo "🔧 Building binary with PyInstaller..."
pyinstaller --clean autotyper.spec

# Check if binary was created
if [[ -f "$DIST_DIR/autotyper" ]]; then
    echo "✅ Binary created successfully!"
    
    # Get binary info
    echo "📊 Binary information:"
    ls -lh "$DIST_DIR/autotyper"
    file "$DIST_DIR/autotyper"
    
    # Test the binary
    echo "🧪 Testing binary..."
    if "$DIST_DIR/autotyper" --help >/dev/null 2>&1; then
        echo "✅ Binary test passed"
    else
        echo "❌ Binary test failed"
        exit 1
    fi
    
    # Test layout dump
    if "$DIST_DIR/autotyper" --dump-layout --layout us >/dev/null 2>&1; then
        echo "✅ Layout dump test passed"
    else
        echo "❌ Layout dump test failed"
        exit 1
    fi
    
    echo ""
    echo "🎉 Build completed successfully!"
    echo "📁 Binary location: $DIST_DIR/autotyper"
    echo ""
    echo "To install system-wide:"
    echo "  sudo cp $DIST_DIR/autotyper /usr/local/bin/"
    echo ""
    echo "To test locally:"
    echo "  $DIST_DIR/autotyper --help"
    
else
    echo "❌ Binary creation failed!"
    exit 1
fi
