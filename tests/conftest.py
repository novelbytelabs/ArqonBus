import os
import sys
import socket
from pathlib import Path
import pytest

# Ensure project root and src/ are on path for imports in tests
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for path in (ROOT, SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


_ROOT_FILE_MARKERS = {
    "test_dispatcher.py": ("unit", "regression"),
    "test_dispatch_integration.py": ("unit", "regression"),
    "test_dispatch_e2e.py": ("e2e", "regression"),
    "test_legacy_dispatch.py": ("unit", "regression"),
    "test_operator_sam.py": ("unit",),
    "test_server_api.py": ("unit",),
    "test_basic.py": ("unit",),
    "test_simple.py": ("unit",),
}


def pytest_collection_modifyitems(config, items):
    """Apply canonical suite markers by test path."""
    for item in items:
        nodeid = item.nodeid
        file_name = Path(nodeid.split("::", 1)[0]).name

        if "tests/performance/" in nodeid:
            item.add_marker(pytest.mark.performance)
            continue

        if "tests/unit/" in nodeid:
            item.add_marker(pytest.mark.unit)
            continue

        if "tests/regression/" in nodeid:
            item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.regression)
            continue

        if "tests/integration/" in nodeid:
            item.add_marker(pytest.mark.integration)
            if "test_e2e_" in file_name or file_name.endswith("_e2e.py"):
                item.add_marker(pytest.mark.e2e)
            continue

        for marker in _ROOT_FILE_MARKERS.get(file_name, ("unit",)):
            item.add_marker(getattr(pytest.mark, marker))


def _socket_capable() -> bool:
    """Check whether this environment allows local TCP socket operations."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            s.listen(1)
        return True
    except OSError:
        return False


def pytest_runtest_setup(item):
    if item.get_closest_marker("socket"):
        if _socket_capable():
            return
        if os.getenv("ARQONBUS_REQUIRE_SOCKET_TESTS", "0") == "1":
            pytest.fail("Socket-marked tests are required but local TCP socket capability is unavailable")
        pytest.skip("Socket capability unavailable in this environment")
