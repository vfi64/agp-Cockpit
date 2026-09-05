from agp_cockpit.adapters import macos_chatgpt as mac

def test_run_osascript_owns_platform_command(monkeypatch):
    seen={}
    class R:
        returncode=0; stdout="ok"; stderr=""
    def fake(argv,**kwargs):
        seen["argv"]=argv; return R()
    monkeypatch.setattr(mac.subprocess,"run",fake)
    assert mac.run_osascript("return 1").stdout == "ok"
    assert seen["argv"] == ["/usr/bin/osascript","-e","return 1"]

def test_open_chatgpt_owns_platform_command(monkeypatch):
    seen={}
    class R:
        returncode=0; stdout=""; stderr=""
    def fake(argv,**kwargs):
        seen["argv"]=argv; return R()
    monkeypatch.setattr(mac.subprocess,"run",fake)
    mac.open_chatgpt_in_chrome()
    assert seen["argv"] == ["/usr/bin/open","-a","Google Chrome","https://chatgpt.com/"]
