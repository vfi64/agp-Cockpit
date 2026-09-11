from pathlib import Path
import pytest
from agp_cockpit.core.terminal_exec import TerminalCommand
from agp_cockpit.core.terminal_policy import ExecutionPolicy

def test_unlisted_tool_denied(tmp_path):
 p=ExecutionPolicy(repository_root=tmp_path,allowed_tools=frozenset({'python'}),allow_network=False)
 with pytest.raises(PermissionError,match='tool is not authorized'): p.validate(TerminalCommand(argv=('curl','x'),cwd=tmp_path))

def test_network_tool_denied(tmp_path):
 p=ExecutionPolicy(repository_root=tmp_path,allowed_tools=frozenset({'curl'}),allow_network=False)
 with pytest.raises(PermissionError,match='network tool is not authorized'): p.validate(TerminalCommand(argv=('curl','x'),cwd=tmp_path))
