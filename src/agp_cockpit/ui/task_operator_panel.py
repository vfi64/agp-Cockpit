import tkinter as tk
from pathlib import Path
from tkinter import messagebox,ttk
from agp_cockpit.core.task_operator_api import TaskOperatorAPI

class TaskOperatorPanel(ttk.Frame):
    def __init__(self,master:tk.Misc,*,repository_root:Path)->None:
        super().__init__(master,padding=12); self.api=TaskOperatorAPI(repository_root); self.repository_root=repository_root.expanduser().resolve()
        self.columnconfigure(0,weight=1); self.columnconfigure(1,weight=0); self.columnconfigure(2,weight=0); self.columnconfigure(3,weight=0); self.rowconfigure(3,weight=1)
        ttk.Label(self,text="Task Operator",font=("TkDefaultFont",13,"bold")).grid(row=0,column=0,columnspan=4,sticky="w")
        self.status_var=tk.StringVar(); ttk.Label(self,textvariable=self.status_var,justify="left",wraplength=680).grid(row=1,column=0,columnspan=4,sticky="ew",pady=(8,8))
        self.focus_var=tk.StringVar(value="Tastaturfokus: —")
        ttk.Label(self,textvariable=self.focus_var,justify="left").grid(row=2,column=0,columnspan=4,sticky="w",pady=(0,8))
        self.refresh_button=ttk.Button(self,text="Status aktualisieren",command=self.refresh,takefocus=True)
        self.pause_button=ttk.Button(self,text="Task pausieren",command=self.pause,takefocus=True)
        self.resume_button=ttk.Button(self,text="Task fortsetzen",command=self.resume,takefocus=True)
        self.approve_button=ttk.Button(self,text="Checkpoint freigeben",command=self.approve,takefocus=True)
        focus_names={
            self.refresh_button:"Status aktualisieren",
            self.pause_button:"Task pausieren",
            self.resume_button:"Task fortsetzen",
            self.approve_button:"Checkpoint freigeben",
        }
        for i,w in enumerate((self.refresh_button,self.pause_button,self.resume_button,self.approve_button)):
            w.grid(row=3,column=i,padx=(0,8),sticky="w")
            w.bind("<FocusIn>",lambda _e,b=w:self.focus_var.set(f"Tastaturfokus: {focus_names[b]}"))
            w.bind("<FocusOut>",lambda _e:self.focus_var.set("Tastaturfokus: —"))
        self.bind_all("<Command-r>",lambda _e:self.refresh()); self.bind_all("<Command-p>",lambda _e:self.pause())
        self.refresh_button.focus_set(); self.refresh()
    def _act(self,fn):
        try: fn(); self.refresh()
        except Exception as exc: messagebox.showerror("Task Operator",str(exc),parent=self.winfo_toplevel())
    def pause(self): self._act(self.api.pause)
    def resume(self): self._act(self.api.resume)
    def approve(self): self._act(self.api.approve_checkpoint)
    def refresh(self):
        s=self.api.status()
        self.status_var.set(f"Repository: {self.repository_root}\nTask-Zustand: {s.get('state','—')}\nUnterbrechung: {s.get('suspension_reason') or '—'}\nHuman-Checkpoint: {s.get('checkpoint_id') or '—'}\nCompletion: {s.get('completion_status') or s.get('state') or '—'}")
