from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]
hiddenimports = collect_submodules("tkinter")

a = Analysis(
    [str(ROOT / "packaging" / "macos" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[(str(ROOT / "chrome_extension"), "chrome_extension")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="AGP Cockpit",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, argv_emulation=False, target_arch=None,
    codesign_identity=None, entitlements_file=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[], name="AGP Cockpit")
app = BUNDLE(
    coll,
    name="AGP Cockpit.app",
    icon=None,
    bundle_identifier="de.vfi64.agp-cockpit",
    version="0.1.0.dev0",
    info_plist={
        "CFBundleDisplayName": "AGP Cockpit",
        "CFBundleName": "AGP Cockpit",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "13.0",
    },
)
