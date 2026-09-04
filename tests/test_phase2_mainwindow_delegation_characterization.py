"""Headless Phase-2 characterization of MainWindow delegation."""
from __future__ import annotations
from types import SimpleNamespace
from agp_cockpit.core.startup import StartupAction
from agp_cockpit.ui import main_window

class Var:
    def __init__(self,value=""): self.value=value
    def get(self): return self.value
    def set(self,value): self.value=value

class Widget:
    def __init__(self): self.options={}
    def configure(self,**kwargs): self.options.update(kwargs)
    def __setitem__(self,key,value): self.options[key]=value
    def __getitem__(self,key): return self.options[key]

def shell():
    w=main_window.MainWindow.__new__(main_window.MainWindow)
    w.ollama_var=Var(); w.hermes_var=Var(); w.model_var=Var(); w.status_var=Var()
    w.model_box=Widget(); w.repair_button=Widget(); w.hermes_model_button=Widget()
    w.update_idletasks=lambda: None
    w.winfo_toplevel=lambda: object()
    return w

def test_refresh_runtime_status_delegates_and_prefers_hermes_model(monkeypatch):
    w=shell()
    obs=SimpleNamespace(ollama_installed=True,port_busy=True,port_owner_is_ollama=True,api_reachable=True,models=("model-a","model-b"))
    decision=SimpleNamespace(action=StartupAction.CONTINUE,message="continue")
    cfg=SimpleNamespace(exists=True,error=None,model="model-b",model_path=("model",))
    hermes=SimpleNamespace(config=cfg)
    monkeypatch.setattr(main_window,"observe_live_read_only",lambda: obs)
    monkeypatch.setattr(main_window,"decide_startup",lambda value: decision)
    monkeypatch.setattr(main_window,"discover_hermes_runtime",lambda *,ollama_models: hermes)
    monkeypatch.setattr(main_window,"format_hermes_status",lambda value:"HERMES OK")
    w.refresh_runtime_status()
    assert w.model_box["values"]==obs.models
    assert w.model_var.get()=="model-b"
    assert w.hermes_var.get()=="HERMES OK"
    assert w.status_var.get()=="Ollama bereit · Hermes geprüft"
    assert w.repair_button.options["state"]=="disabled"
    assert w.hermes_model_button.options["state"]=="normal"

def test_refresh_runtime_status_fail_closed_on_diagnostic_error(monkeypatch):
    w=shell()
    monkeypatch.setattr(main_window,"observe_live_read_only",lambda: (_ for _ in ()).throw(RuntimeError("probe failed")))
    w.refresh_runtime_status()
    assert w.status_var.get()=="Diagnosefehler: probe failed"
    assert w.model_box["values"]==()
    assert w.model_var.get()==""
    assert w.repair_button.options["state"]=="disabled"
    assert w.hermes_model_button.options["state"]=="disabled"

def test_guarded_ollama_action_delegates_without_live_process(monkeypatch):
    w=shell(); events=[]
    w.refresh_runtime_status=lambda: events.append("refresh")
    result=SimpleNamespace(ok=True,decision=SimpleNamespace(message="ready"))
    monkeypatch.setattr(main_window,"execute_live_guarded_startup",lambda: result)
    monkeypatch.setattr(main_window.messagebox,"showinfo",lambda *a,**k: events.append(("info",a)))
    monkeypatch.setattr(main_window.messagebox,"showwarning",lambda *a,**k: events.append(("warning",a)))
    monkeypatch.setattr(main_window.messagebox,"showerror",lambda *a,**k: events.append(("error",a)))
    w.run_guarded_ollama_action()
    assert events[0]=="refresh"
    assert events[1][0]=="info"

def test_apply_selected_model_requires_confirmation_before_writer(monkeypatch):
    w=shell(); w.model_var.set("model-b"); writes=[]
    monkeypatch.setattr(main_window.messagebox,"askyesno",lambda *a,**k: False)
    monkeypatch.setattr(main_window,"update_hermes_model",lambda *a,**k: writes.append((a,k)))
    w.apply_selected_model_to_hermes()
    assert writes==[]

def test_apply_selected_model_delegates_to_writer_after_confirmation(monkeypatch,tmp_path):
    w=shell(); w.model_var.set("model-b"); events=[]; calls=[]
    w.refresh_runtime_status=lambda: events.append("refresh")
    monkeypatch.setattr(main_window.messagebox,"askyesno",lambda *a,**k: True)
    monkeypatch.setattr(main_window.messagebox,"showinfo",lambda *a,**k: events.append(("info",a)))
    monkeypatch.setattr(main_window.messagebox,"showerror",lambda *a,**k: events.append(("error",a)))
    result=SimpleNamespace(new_model="model-b",backup_path=tmp_path/"backup.yaml")
    monkeypatch.setattr(main_window,"update_hermes_model",lambda model,*,path: calls.append((model,path)) or result)
    w.apply_selected_model_to_hermes()
    assert calls==[("model-b",main_window.DEFAULT_HERMES_CONFIG)]
    assert events[0]=="refresh"
    assert events[1][0]=="info"
