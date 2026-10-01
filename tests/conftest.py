import pytest


# Safety boundary: tests must never resolve product user state to the operator's real HOME.
@pytest.fixture(autouse=True)
def _isolate_agp_cockpit_user_state(tmp_path, monkeypatch):
    test_home = tmp_path / 'home'
    test_home.mkdir()
    monkeypatch.setenv('HOME', str(test_home))



# AGP_KIT_INSTALLATION_AUTHORITY_V1: tests use their fixture manifest unless a
# test opts into Kit discovery explicitly (the CI image installs the real Kit).
@pytest.fixture(autouse=True)
def _no_installed_kit_discovery(monkeypatch):
    monkeypatch.setenv("AGP_COCKPIT_KIT_BINARY", "none")
