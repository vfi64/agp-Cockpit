from agp_cockpit.core.runtime import process_name_present


class FakeProcessPort:
    def __init__(self, running):
        self.running={name.casefold() for name in running}; self.queries=[]
    def is_running(self, process_name):
        self.queries.append(process_name); return process_name.casefold() in self.running

def test_process_presence_uses_port_without_os_access():
    fake=FakeProcessPort({"ollama"})
    assert process_name_present("OLLAMA", process_port=fake) is True
    assert process_name_present("hermes", process_port=fake) is False
    assert fake.queries == ["OLLAMA", "hermes"]

def test_injected_process_lines_remain_portable_characterization():
    lines=("100 /opt/homebrew/bin/ollama serve", "200 /bin/zsh")
    assert process_name_present("OLLAMA", process_lines=lines) is True
    assert process_name_present("hermes", process_lines=lines) is False
