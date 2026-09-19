from __future__ import annotations

import threading

from agp_cockpit.core.task_controller import DurableTaskController


def test_session_controller_cross_thread_access(tmp_path):
    c=DurableTaskController("threaded",tmp_path/"runtime.sqlite3")
    c.accept_remote_action("a1",{"x":1});n=c.begin_attempt("a1");c.record_local_result("a1",n,"FAIL","failure")
    seen=[]
    def worker(): seen.append([x["action_id"] for x in c.pending_results()])
    t=threading.Thread(target=worker);t.start();t.join(timeout=3)
    assert seen==[["a1"]]
    c.close()

def test_same_session_concurrent_dispatch_is_serialized(tmp_path):
    c=DurableTaskController("threaded",tmp_path/"runtime.sqlite3")
    c.accept_remote_action("a1",{"x":1});c.accept_remote_action("a2",{"x":2})
    barrier=threading.Barrier(3);results=[]
    def worker(a):
        barrier.wait()
        try: results.append((a,"OK",c.begin_attempt(a)))
        except Exception as e:  # noqa: BLE001 - the test records the actual concurrency error.
            results.append((a,type(e).__name__,str(e)))
    a=threading.Thread(target=worker,args=("a1",));d=threading.Thread(target=worker,args=("a2",))
    a.start();d.start();barrier.wait();a.join();d.join()
    assert sum(x[1]=="OK" for x in results)==1
    assert any("another action is already executing" in str(x) for x in results)
    c.close()
