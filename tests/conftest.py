import os
import sys
from pathlib import Path

# Ensure project root and src/ are on path for imports in tests
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for path in (ROOT, SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
