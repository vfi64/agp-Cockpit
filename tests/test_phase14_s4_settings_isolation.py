from pathlib import Path


def test_structured_startup_stubs_settings_loader():
    source=Path('tests/test_phase11_structured_startup.py').read_text(encoding='utf-8')
    assert 'agp_cockpit.settings.load_and_migrate_settings' in source
    assert 'agp_cockpit.app.settings_path' not in source
    assert 'agp_cockpit.adapters.macos_settings.settings_path' not in source

def test_production_runtime_root_remains_application_support():
    from agp_cockpit.adapters.macos_settings import bridge_runtime_root, settings_path
    assert bridge_runtime_root() == settings_path().parent / 'bridge'
    assert 'Application Support/AGP Cockpit/bridge' in str(bridge_runtime_root())
