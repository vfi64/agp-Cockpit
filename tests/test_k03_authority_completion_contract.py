from pathlib import Path
import pytest
from agp_cockpit.core.task_controller import DurableTaskController
from agp_cockpit.core.task_models import KitResultEvidence
from agp_cockpit.core.terminal_exec import TerminalCommand
from agp_cockpit.core.terminal_policy import ExecutionPolicy
def ctl(t): return DurableTaskController("k03",t/"task.sqlite3")
def ev(): return KitResultEvidence(action_id="kit-final",status="PASS",producer="agentic-project-kit",command=("agentic-kit","check"),revision="rev",artifact_hash="artifact",raw_hash="raw")
def prepare(c):
 c.accept_remote_action("kit-final",{"effect":"E3","kind":"kit"});n=c.begin_attempt("kit-final");c.record_local_result("kit-final",n,"PASS","observed");c.mark_result_delivered(c.pending_results()[0]["message_id"]);c.store.set_states(c.task_id,governance_state="CLEAR",execution_state="SUCCEEDED")
def test_local_authority(tmp_path):
 c=ctl(tmp_path);c.set_task_authority(repository_root=tmp_path,allowed_effects=("E0",),allowed_tools=("echo",));assert c.action_authorized({"effect":"E0","argv":["echo"],"cwd":str(tmp_path)});assert not c.action_authorized({"effect":"E2","argv":["echo"],"cwd":str(tmp_path)});assert not c.action_authorized({"effect":"E0","argv":["python"],"cwd":str(tmp_path)})
def test_policy(tmp_path):
 p=ExecutionPolicy(tmp_path,allowed_tools=frozenset({"echo"}),allow_network=False);p.validate(TerminalCommand(("echo","ok"),tmp_path))
 with pytest.raises(PermissionError,match="tool"):p.validate(TerminalCommand(("python","-c","print(1)"),tmp_path))
 p2=ExecutionPolicy(tmp_path,allow_network=False)
 with pytest.raises(PermissionError,match="network"):p2.validate(TerminalCommand(("curl","x"),tmp_path))
def test_untrusted(tmp_path):
 c=ctl(tmp_path);prepare(c);c.record_kit_result(ev());c.set_completion_contract("rev","artifact","kit-final","raw");assert c.propose_complete();assert not c.verify_completion_contract();assert c.completion_contract()["rejection_reason"]=="UNTRUSTED_KIT_EVIDENCE"
def test_trusted(tmp_path):
 c=ctl(tmp_path);prepare(c);c.record_verified_kit_result(ev(),acquisition_source="local-executor");c.set_completion_contract("rev","artifact","kit-final","raw");assert c.propose_complete();assert c.verify_completion_contract()
