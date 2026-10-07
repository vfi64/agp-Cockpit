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


# AGP_GH_BINARY_V1: no test may depend on the host's gh installation or login
# (PR #141: green on the developer's Mac, red on the CI runner). Tests that
# need gh point AGP_COCKPIT_GH_BINARY at their own fake.
@pytest.fixture(autouse=True)
def _no_host_gh(monkeypatch):
    monkeypatch.setenv("AGP_COCKPIT_GH_BINARY", "none")


# AGP_RUNTIME_HOME_V1 (PR #272, CI red): app.main() announces the runtime home in the
# process environment; a test that ran main() moved the runtime of every later test into
# a foreign folder. Every test starts without it; the empty value is restored to "unset".
@pytest.fixture(autouse=True)
def _no_runtime_home(monkeypatch):
    monkeypatch.setenv("AGP_COCKPIT_RUNTIME_HOME", "")
