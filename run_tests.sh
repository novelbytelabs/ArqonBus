#!/bin/bash
# ArqonBus Test Runner Script
# This script uses the correct Python environment for testing

echo "Running ArqonBus tests..."
/home/irbsurfer/miniconda3/envs/helios-gpu-118/bin/python -m pytest "$@"