import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app
from app.routers.auth import get_current_user

@pytest.fixture(autouse=True)
def bypass_auth_globally():
    """Globally bypass signed cookie session authentication for existing test suites."""
    app.dependency_overrides[get_current_user] = lambda: "admin"
    yield
    app.dependency_overrides.pop(get_current_user, None)

