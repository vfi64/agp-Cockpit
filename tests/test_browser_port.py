from agp_cockpit.core.browser_transport import focus_chrome, open_url_in_chrome

class FakeBrowserPort:
    def __init__(self, installed=True):
        self._installed=installed; self.focused=False; self.urls=[]
    def installed(self): return self._installed
    def focus(self): self.focused=True
    def open_url(self,url): self.urls.append(url)

def test_core_browser_transport_uses_port_without_platform_access():
    fake=FakeBrowserPort()
    focus_chrome(fake)
    open_url_in_chrome("https://chatgpt.com/",fake)
    assert fake.focused is True
    assert fake.urls==["https://chatgpt.com/"]

def test_core_browser_transport_blocks_missing_browser_via_port():
    fake=FakeBrowserPort(installed=False)
    try:
        focus_chrome(fake)
    except RuntimeError as exc:
        assert "nicht gefunden" in str(exc)
    else:
        raise AssertionError("missing browser must fail closed")
