"""Singletons compartidos entre routers (state manager + notificadores)."""
import sys
from pathlib import Path

# Allow `capture.*` imports from project root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from capture.state import DetectionStateManager

state_manager = DetectionStateManager()
