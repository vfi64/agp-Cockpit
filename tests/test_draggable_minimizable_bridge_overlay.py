from pathlib import Path

def test_overlay_is_draggable_and_minimizable():
    source = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    assert "AGP_OVERLAY_DRAG_MINIMIZE_063S2" in source
    assert "beginOverlayDrag" in source
    assert 'window.addEventListener("mousemove", moveOverlayDrag)' in source
    assert 'window.addEventListener("mouseup", endOverlayDrag)' in source
    assert "agpOverlayUi063S2" in source
    assert "chrome.storage.local.set" in source
    assert 'className = "agp-minimize"' in source
    assert 'root.classList.toggle("agp-minimized"' in source
    assert 'event.target.closest("button")' in source

def test_overlay_default_fixed_position_is_preserved():
    source = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    assert "position:fixed;right:18px;bottom:88px" in source
    assert 'root.style.right = "auto"' in source
    assert 'root.style.bottom = "auto"' in source
