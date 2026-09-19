import hashlib
from pathlib import Path

import pytest

from agp_cockpit.core.kit_carrier import KitAuthorityResult
from agp_cockpit.core.task_controller import DurableTaskController
from agp_cockpit.core.task_models import KitResultEvidence
from agp_cockpit.core.terminal_exec import TerminalResult
from agp_cockpit.core.work_order_runner import (
 WorkOrderRun,
 acquire_trusted_kit_evidence,
)


def ro(tmp_path,rc=0,argv=("agentic-kit","check"),accepted=True,out="ok"):
 return WorkOrderRun(TerminalResult(tuple(argv),tmp_path,rc,out,"",False,0.01),f"RC={rc}\n{out}",KitAuthorityResult(True,0,"{}","",accepted,"accepted"))
def test_local_pass_is_trusted(tmp_path):
 c=DurableTaskController("t",tmp_path/"d");c.accept_remote_action("a",{"x":1});n=c.begin_attempt("a");c.record_local_result("a",n,"PASS","x");c.mark_result_delivered(c.pending_results()[0]["message_id"]);e=c.acquire_and_record_verified_kit_result("a",ro(tmp_path),repository_root=Path.cwd());r=c.store.kit_evidence_for("t","a");assert e.status=="PASS" and r["trusted"]==1 and r["acquisition_source"]=="local-kit-execution"
def test_caller_pass_untrusted(tmp_path):
 c=DurableTaskController("t",tmp_path/"d");c.accept_remote_action("a",{"x":1});n=c.begin_attempt("a");c.record_local_result("a",n,"PASS","x");e=KitResultEvidence("a","PASS","agentic-project-kit",("agentic-kit","check"),"r","h",hashlib.sha256(b"x").hexdigest());c.record_kit_result(e);assert c.store.kit_evidence_for("t","a")["trusted"]==0
def test_nonkit_rejected(tmp_path):
 r=WorkOrderRun(TerminalResult(("python","-V"),tmp_path,0,"","",False,.01),"",KitAuthorityResult(False,None,"","",True,"generic"))
 with pytest.raises(PermissionError):acquire_trusted_kit_evidence("a",r,repository_root=Path.cwd())
def test_fail_not_promoted(tmp_path):assert acquire_trusted_kit_evidence("a",ro(tmp_path,rc=2),repository_root=Path.cwd()).status=="FAIL"
def test_raw_mutation_changes_hash(tmp_path):assert acquire_trusted_kit_evidence("a",ro(tmp_path,out="1"),repository_root=Path.cwd()).raw_hash!=acquire_trusted_kit_evidence("a",ro(tmp_path,out="2"),repository_root=Path.cwd()).raw_hash
