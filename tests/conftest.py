import pytest

# Safety boundary: tests must never resolve product user state to the operator's real HOME.
@pytest.fixture(autouse=True)
def _isolate_agp_cockpit_user_state(tmp_path, monkeypatch):
    test_home = tmp_path / 'home'
    test_home.mkdir()
    monkeypatch.setenv('HOME', str(test_home))

