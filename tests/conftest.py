import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Main


@pytest.fixture(autouse=True)
def clean_tree():
    previous = list(Main.tree)
    previous_registry = dict(Main.name_registry)
    previous_auto_used_names = set(Main.auto_used_names)
    Main.tree.clear()
    Main.name_registry.clear()
    Main.auto_used_names.clear()
    try:
        yield
    finally:
        Main.tree.clear()
        Main.tree.extend(previous)
        Main.name_registry.clear()
        Main.name_registry.update(previous_registry)
        Main.auto_used_names.clear()
        Main.auto_used_names.update(previous_auto_used_names)
