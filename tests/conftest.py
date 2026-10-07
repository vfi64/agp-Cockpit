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


# AGP_INVISIBLE_TEST_WINDOWS_V1 (owner 2026-10-07, release 0.2.2): the Kit's local feature
# gate runs this suite on the owner's Mac, and every GUI test flashed a real Cockpit window
# in an odd size. Test windows are fully transparent; geometry, mapping and events are
# unchanged, so the layout tests measure the same. AGP_TEST_SHOW_WINDOWS=1 shows them.
def _hide_window(window) -> None:
    try:
        window.attributes("-alpha", 0.0)
    except Exception:  # noqa: BLE001, S110 - a platform without alpha keeps its window
        pass


@pytest.fixture(autouse=True, scope="session")
def _invisible_test_windows():
    import os
    if os.environ.get("AGP_TEST_SHOW_WINDOWS") == "1":
        yield
        return
    try:
        import tkinter
    except ImportError:
        yield
        return
    originals = {cls: cls.__init__ for cls in (tkinter.Tk, tkinter.Toplevel)}

    def wrap(cls):
        original = originals[cls]

        def __init__(self, *args, **kwargs):
            original(self, *args, **kwargs)
            _hide_window(self)
        return __init__

    for cls in originals:
        cls.__init__ = wrap(cls)
    try:
        yield
    finally:
        for cls, original in originals.items():
            cls.__init__ = original


# AGP_START_WAITS_FOR_EXTENSION_V1: no browser runs in the suite; a start never waits for the
# extension unless a test turns the gate on (tests/test_start_after_rebuild.py).
@pytest.fixture(autouse=True)
def _no_extension_gate(monkeypatch):
    monkeypatch.setenv("AGP_COCKPIT_EXTENSION_GATE", "off")
