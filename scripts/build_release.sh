#!/bin/bash
set -e

# Configuration
SENTINEL_CRATE_DIR="../ArqonSentinel/crates/arqon_sentinel_python"
DIST_DIR="$(pwd)/dist_artifacts"

echo "==============================================="
echo "   ARQON TOPOLOGICAL TRUTH ENGINE: BUILDER    "
echo "==============================================="
echo "Target Crate: $SENTINEL_CRATE_DIR"
echo "Output Dir:   $DIST_DIR"

# 1. Prepare Output Directory
mkdir -p "$DIST_DIR"
rm -rf "$DIST_DIR/*"

# 2. Build Rust Wheel (Maturin)
echo ""
echo "[1/3] Compiling Rust Kernel (Release Mode)..."
# We assume we are in the 'scripts' dir or ArqonBus root. 
# Let's handle directory logic safely.
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

if ! command -v maturin &> /dev/null; then
    echo "❌ Maturin not found. Please install it: pip install maturin"
    exit 1
fi

# Need to run maturin from the crate dir or point to it
cd "$SENTINEL_CRATE_DIR"
maturin build --release --out "$DIST_DIR"

# 3. Verify Artifact
echo ""
echo "[2/3] Verifying Artifact..."
cd "$DIST_DIR"
WHEEL_FILE=$(ls *.whl | head -n 1)

if [ -z "$WHEEL_FILE" ]; then
    echo "❌ Build Failed: No wheel file found in $DIST_DIR"
    exit 1
fi

echo "✅ Generated: $WHEEL_FILE"

# 4. Summary
echo ""
echo "[3/3] Build Complete."
echo "Artifact location: $DIST_DIR/$WHEEL_FILE"
echo "Ready for deployment."
