import importlib


def test_module_entrypoint_exists():
    module = importlib.import_module("agp_cockpit.__main__")
    assert hasattr(module, "main")
