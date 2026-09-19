from pathlib import Path

RUNTIME_ROOT=Path("src/agp_cockpit")
FORBIDDEN_STATES={"ORDER_PUBLISHING","WAITING_FOR_REMOTE_RESULT","REMOTE_VISIBLE","RESULT_FETCHING"}
FORBIDDEN_MODULE_FRAGMENTS={"github","transfer_order","remote_poll","remote_sync","result_correlation"}
def runtime_files(): return sorted(p for p in RUNTIME_ROOT.rglob("*.py") if "__pycache__" not in p.parts)
def test_phase9_no_kit_internal_file_transfer_states_in_runtime():
    offenders=[]
    for p in runtime_files():
        text=p.read_text(encoding="utf-8")
        offenders += [f"{p}:{x}" for x in FORBIDDEN_STATES if x in text]
    assert offenders==[]
def test_phase9_no_cockpit_owned_transfer_or_github_modules():
    offenders=[]
    for p in runtime_files():
        low=str(p).lower()
        offenders += [f"{p}:{x}" for x in FORBIDDEN_MODULE_FRAGMENTS if x in low]
    assert offenders==[]
