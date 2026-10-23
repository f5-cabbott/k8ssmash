import os
import tempfile

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    """Tests must never read or write the real user config."""
    monkeypatch.setenv("K8SSMASH_CONFIG", str(tmp_path / "config.json"))
