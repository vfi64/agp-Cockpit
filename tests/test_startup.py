from agp_cockpit.core.startup import (
    StartupAction,
    StartupHooks,
    StartupObservation,
    decide_startup,
    execute_guarded_startup,
)


def O(**kw):
    d = {"ollama_installed": True, "port_busy": False,
             "port_owner_is_ollama": False, "api_reachable": False, "models": ()}
    d.update(kw)
    return StartupObservation(**d)

def test_missing_install_blocks():
    assert decide_startup(O(ollama_installed=False)).action is StartupAction.BLOCK

def test_foreign_owner_blocks():
    d = decide_startup(O(port_busy=True))
    assert d.action is StartupAction.BLOCK and not d.may_mutate

def test_healthy_is_reused():
    d = decide_startup(O(port_busy=True, port_owner_is_ollama=True,
                         api_reachable=True, models=("qwen",)))
    assert d.action is StartupAction.CONTINUE and not d.may_mutate

def test_empty_models_blocks():
    assert decide_startup(O(port_busy=True, port_owner_is_ollama=True,
                            api_reachable=True)).action is StartupAction.BLOCK

def test_stopped_requests_start():
    assert decide_startup(O()).action is StartupAction.START_OLLAMA

def test_unhealthy_ollama_requests_recovery():
    assert decide_startup(O(port_busy=True, port_owner_is_ollama=True)).action is StartupAction.RECOVER_OLLAMA

def test_foreign_owner_never_mutated():
    calls = []
    r = execute_guarded_startup(StartupHooks(
        lambda: O(port_busy=True),
        lambda: calls.append("start"),
        lambda: calls.append("recover")))
    assert not r.ok and calls == []

def test_healthy_never_restarted():
    calls = []
    r = execute_guarded_startup(StartupHooks(
        lambda: O(port_busy=True, port_owner_is_ollama=True,
                  api_reachable=True, models=("qwen",)),
        lambda: calls.append("start"),
        lambda: calls.append("recover")))
    assert r.ok and calls == []

def test_start_converges():
    states = iter((O(), O(port_busy=True, port_owner_is_ollama=True,
                          api_reachable=True, models=("qwen",))))
    calls = []
    r = execute_guarded_startup(StartupHooks(
        lambda: next(states), lambda: calls.append("start"),
        lambda: calls.append("recover")))
    assert r.ok and calls == ["start"]

def test_recovery_converges():
    states = iter((O(port_busy=True, port_owner_is_ollama=True),
                   O(port_busy=True, port_owner_is_ollama=True,
                     api_reachable=True, models=("qwen",))))
    calls = []
    r = execute_guarded_startup(StartupHooks(
        lambda: next(states), lambda: calls.append("start"),
        lambda: calls.append("recover")))
    assert r.ok and calls == ["recover"]
