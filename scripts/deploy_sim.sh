#!/bin/bash
set -e

# Configuration
DIST_DIR="$(pwd)/dist_artifacts"
VENV_DIR="/tmp/arqon_deploy_sim_venv"

echo "==============================================="
echo "   ARQON DEPLOYMENT SIMULATOR (Option B)      "
echo "==============================================="

# 1. Locate Artifact
WHEEL_FILE=$(find "$DIST_DIR" -name "*.whl" | head -n 1)

if [ -z "$WHEEL_FILE" ]; then
    echo "❌ No artifact found. Please run build_release.sh first."
    exit 1
fi

echo "Deploying Artifact: $WHEEL_FILE"

# 2. Setup Fresh Environment
echo ""
echo "[1/3] creating Isolated Runtime Environment..."
rm -rf "$VENV_DIR"
python -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 3. Install Artifact
echo ""
echo "[2/3] Installing Wheel (Pip)..."
pip install --upgrade pip
pip install "$WHEEL_FILE"

# 4. Verify Installation
echo ""
echo "[3/3] Runtime Verification..."
python3 -c "
import arqon_sentinel
print(f'✅ Import Successful: {arqon_sentinel}')
dsu = arqon_sentinel.ParityDSU(10)
print(f'✅ Kernel Initialized: {dsu}')
"

echo ""
echo "Deployment Simulation SUCCESS."
echo "Cleaned up: $VENV_DIR"
rm -rf "$VENV_DIR"
