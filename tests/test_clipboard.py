class FakeRoot:
    def __init__(self):
        self.value = None
        self.updated = False

    def clipboard_clear(self):
        self.value = ""

    def clipboard_append(self, text):
        self.value = text

    def update_idletasks(self):
        self.updated = True


def test_copy_text():
    from agp_cockpit.core.clipboard import copy_text

    root = FakeRoot()
    result = copy_text(root, "abc")

    assert root.value == "abc"
    assert root.updated is True
    assert result.characters == 3
