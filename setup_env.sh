#!/bin/bash
# ArqonBus Environment Setup Script
# Source this file to set up the development environment

# Add source directory to Python path
export PYTHONPATH="/home/irbsurfer/Projects/arqon/ArqonBus/src:$PYTHONPATH"

# Set Python executable to use for testing
export ARQONBUS_PYTHON="python3"

echo "✅ ArqonBus environment configured:"
echo "   - PYTHONPATH includes /home/irbsurfer/Projects/arqon/ArqonBus/src"
echo "   - Python executable: $(which $ARQONBUS_PYTHON)"
echo "   - Python version: $($ARQONBUS_PYTHON --version)"
echo ""
echo "📋 Run tests with:"
echo "   export PYTHONPATH=\"/home/irbsurfer/Projects/arqon/ArqonBus/src:\$PYTHONPATH\" && pytest"
echo ""
echo "📋 Or use the shortcut:"
echo "   source setup_env.sh && pytest"