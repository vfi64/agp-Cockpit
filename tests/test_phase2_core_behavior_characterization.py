from pathlib import Path

from agp_cockpit.core import hermes_runtime
from agp_cockpit.core.hermes_config import detect_model_path
from agp_cockpit.core.hermes_runtime import discover_hermes_runtime
from agp_cockpit.core.startup import StartupAction, StartupObservation, decide_startup


def obs(**kw):
    base={"ollama_installed": True,"port_busy": False,"port_owner_is_ollama": False,"api_reachable": False,"models": ()}
    base.update(kw)
    return StartupObservation(**base)

def test_startup_decision_matrix_core_cases():
    assert decide_startup(obs(ollama_installed=False)).action is StartupAction.BLOCK
    assert decide_startup(obs(port_busy=True,port_owner_is_ollama=False)).action is StartupAction.BLOCK
    assert decide_startup(obs(api_reachable=True,models=("m",))).action is StartupAction.CONTINUE
    assert decide_startup(obs(port_busy=True,port_owner_is_ollama=True,api_reachable=False)).action is StartupAction.RECOVER_OLLAMA
    assert decide_startup(obs()).action is StartupAction.START_OLLAMA

def test_detect_model_path_prefers_unambiguous_canonical_field():
    data={"model":"qwen3.5:9b-mlx","other":{"model":"secondary"}}
    assert detect_model_path(data, known_models=("qwen3.5:9b-mlx",)) == (("model",), "qwen3.5:9b-mlx")

def test_hermes_runtime_discovery_can_be_fully_isolated(monkeypatch,tmp_path):
    class Exe:
        installed=True
        path=Path("/fake/hermes")
    class Cfg:
        exists=True
        model="qwen3.5:9b-mlx"
        error=None
        model_path=("model",)
    monkeypatch.setattr(hermes_runtime,"find_executable",lambda *a,**k: Exe())
    monkeypatch.setattr(hermes_runtime,"read_hermes_config",lambda *a,**k: Cfg())
    info=discover_hermes_runtime(ollama_models=("qwen3.5:9b-mlx",),config_path=tmp_path/"config.yaml")
    assert info.executable.installed is True
    assert info.config.model == "qwen3.5:9b-mlx"
    assert info.configured_model_available is True
