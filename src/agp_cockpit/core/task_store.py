from __future__ import annotations
import hashlib, json, sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
SCHEMA_VERSION=1
@dataclass(frozen=True)
class StoredAction:
    task_id:str; action_id:str; payload_hash:str; payload_json:str; status:str; attempt_count:int; predecessor_action_id:str|None
class TaskStore:
    def __init__(self,path:str|Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path); self.db.row_factory=sqlite3.Row; self.db.execute('PRAGMA foreign_keys = ON'); self._init()
    def close(self): self.db.close()
    def _init(self):
        with self.db:
            self.db.executescript('''
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks(task_id TEXT PRIMARY KEY,state TEXT NOT NULL,execution_state TEXT NOT NULL,governance_state TEXT NOT NULL,remote_rounds_used INTEGER NOT NULL DEFAULT 0,local_actions_used INTEGER NOT NULL DEFAULT 0,retries_used INTEGER NOT NULL DEFAULT 0,no_progress_rounds INTEGER NOT NULL DEFAULT 0,controller_generation INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS actions(task_id TEXT NOT NULL,action_id TEXT NOT NULL,payload_hash TEXT NOT NULL,payload_json TEXT NOT NULL,status TEXT NOT NULL,attempt_count INTEGER NOT NULL DEFAULT 0,predecessor_action_id TEXT,PRIMARY KEY(task_id,action_id),FOREIGN KEY(task_id) REFERENCES tasks(task_id));
CREATE TABLE IF NOT EXISTS attempts(task_id TEXT NOT NULL,action_id TEXT NOT NULL,attempt_no INTEGER NOT NULL,status TEXT NOT NULL,result_json TEXT,PRIMARY KEY(task_id,action_id,attempt_no),FOREIGN KEY(task_id,action_id) REFERENCES actions(task_id,action_id));
CREATE TABLE IF NOT EXISTS messages(message_id INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT NOT NULL,direction TEXT NOT NULL,kind TEXT NOT NULL,action_id TEXT,payload_json TEXT NOT NULL,delivered INTEGER NOT NULL DEFAULT 0,FOREIGN KEY(task_id) REFERENCES tasks(task_id));
CREATE TABLE IF NOT EXISTS evidence(evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT NOT NULL,action_id TEXT NOT NULL,outcome TEXT NOT NULL,summary TEXT NOT NULL,governance_blocked INTEGER NOT NULL DEFAULT 0,FOREIGN KEY(task_id,action_id) REFERENCES actions(task_id,action_id));
''')
            r=self.db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if r is None:self.db.execute("INSERT INTO metadata(key,value) VALUES('schema_version',?)",(str(SCHEMA_VERSION),))
            elif int(r['value'])!=SCHEMA_VERSION:raise RuntimeError('unsupported task-store schema version')
    @staticmethod
    def canonical_payload(payload:Any)->str:return json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    @classmethod
    def payload_hash(cls,payload:Any)->str:return hashlib.sha256(cls.canonical_payload(payload).encode()).hexdigest()
    def ensure_task(self,task_id:str):
        with self.db:self.db.execute("INSERT OR IGNORE INTO tasks(task_id,state,execution_state,governance_state) VALUES(?,?,?,?)",(task_id,'ACTIVE','IDLE','CLEAR'))
    def task_row(self,task_id:str):
        r=self.db.execute('SELECT * FROM tasks WHERE task_id=?',(task_id,)).fetchone()
        if r is None:raise KeyError(task_id)
        return r
    def set_states(self,task_id:str,state=None,execution_state=None,governance_state=None):
        r=self.task_row(task_id)
        with self.db:self.db.execute('UPDATE tasks SET state=?,execution_state=?,governance_state=? WHERE task_id=?',(state or r['state'],execution_state or r['execution_state'],governance_state or r['governance_state'],task_id))
    def bump(self,task_id:str,field:str,n:int=1):
        if field not in {'remote_rounds_used','local_actions_used','retries_used','no_progress_rounds'}:raise ValueError('unsupported budget field')
        with self.db:self.db.execute(f'UPDATE tasks SET {field}={field}+? WHERE task_id=?',(n,task_id))
    def register_action(self,task_id,action_id,payload,predecessor_action_id=None):
        self.ensure_task(task_id); canonical=self.canonical_payload(payload); digest=self.payload_hash(payload)
        r=self.db.execute('SELECT * FROM actions WHERE task_id=? AND action_id=?',(task_id,action_id)).fetchone()
        if r is not None:
            if r['payload_hash']!=digest:raise ValueError('action_id reused with changed payload')
            return 'DUPLICATE'
        if predecessor_action_id:
            p=self.db.execute('SELECT status FROM actions WHERE task_id=? AND action_id=?',(task_id,predecessor_action_id)).fetchone()
            if p is None:raise ValueError('unknown predecessor')
            if p['status']=='OUTCOME_UNKNOWN':raise RuntimeError('predecessor outcome unresolved')
        with self.db:
            self.db.execute('INSERT INTO actions(task_id,action_id,payload_hash,payload_json,status,predecessor_action_id) VALUES(?,?,?,?,?,?)',(task_id,action_id,digest,canonical,'REGISTERED',predecessor_action_id))
            self.db.execute("INSERT INTO messages(task_id,direction,kind,action_id,payload_json,delivered) VALUES(?,?,?,?,?,1)",(task_id,'IN','ACTION',action_id,canonical))
        return 'NEW'
    def begin_attempt(self,task_id,action_id):
        r=self.db.execute('SELECT * FROM actions WHERE task_id=? AND action_id=?',(task_id,action_id)).fetchone()
        if r is None:raise KeyError(action_id)
        if r['status']=='OUTCOME_UNKNOWN':raise RuntimeError('cannot retry unresolved outcome')
        no=int(r['attempt_count'])+1
        with self.db:
            self.db.execute("UPDATE actions SET attempt_count=?,status='DISPATCH_INTENT' WHERE task_id=? AND action_id=?",(no,task_id,action_id))
            self.db.execute("INSERT INTO attempts(task_id,action_id,attempt_no,status) VALUES(?,?,?,'DISPATCH_INTENT')",(task_id,action_id,no))
            self.bump(task_id,'local_actions_used'); self.set_states(task_id,state='ACTIVE',execution_state='RUNNING')
        return no
    def record_result(self,task_id,action_id,attempt_no,outcome,summary,governance_blocked=False):
        o=outcome.upper()
        if o not in {'PASS','FAIL','BLOCKED'}:raise ValueError('unsupported outcome')
        es={'PASS':'SUCCEEDED','FAIL':'FAILED','BLOCKED':'BLOCKED'}[o]
        payload=self.canonical_payload({'outcome':o,'summary':summary,'governance_blocked':governance_blocked})
        with self.db:
            self.db.execute('UPDATE attempts SET status=?,result_json=? WHERE task_id=? AND action_id=? AND attempt_no=?',(o,payload,task_id,action_id,attempt_no))
            self.db.execute('UPDATE actions SET status=? WHERE task_id=? AND action_id=?',(o,task_id,action_id))
            self.db.execute('INSERT INTO evidence(task_id,action_id,outcome,summary,governance_blocked) VALUES(?,?,?,?,?)',(task_id,action_id,o,summary,1 if governance_blocked else 0))
            self.db.execute("INSERT INTO messages(task_id,direction,kind,action_id,payload_json,delivered) VALUES(?,?,?,?,?,0)",(task_id,'OUT','RESULT',action_id,payload))
            self.set_states(task_id,state='WAITING_FOR_REMOTE',execution_state=es,governance_state='BLOCKED' if governance_blocked or o=='BLOCKED' else 'CLEAR')
    def mark_unknown(self,task_id,action_id,attempt_no,reason):
        with self.db:
            self.db.execute("UPDATE attempts SET status='OUTCOME_UNKNOWN',result_json=? WHERE task_id=? AND action_id=? AND attempt_no=?",(self.canonical_payload({'reason':reason}),task_id,action_id,attempt_no))
            self.db.execute("UPDATE actions SET status='OUTCOME_UNKNOWN' WHERE task_id=? AND action_id=?",(task_id,action_id))
            self.set_states(task_id,state='RECONCILING',execution_state='OUTCOME_UNKNOWN')
    def reconcile(self,task_id,action_id,conclusion):
        if conclusion not in {'CONFIRMED_APPLIED','CONFIRMED_NOT_APPLIED','STILL_UNKNOWN'}:raise ValueError('invalid reconciliation conclusion')
        r=self.db.execute('SELECT status FROM actions WHERE task_id=? AND action_id=?',(task_id,action_id)).fetchone()
        if r is None or r['status']!='OUTCOME_UNKNOWN':raise RuntimeError('action is not outcome-unknown')
        if conclusion=='STILL_UNKNOWN':self.set_states(task_id,state='SUSPENDED',execution_state='OUTCOME_UNKNOWN'); return
        st='RECONCILED_APPLIED' if conclusion=='CONFIRMED_APPLIED' else 'RECONCILED_NOT_APPLIED'
        with self.db:
            self.db.execute('UPDATE actions SET status=? WHERE task_id=? AND action_id=?',(st,task_id,action_id))
            self.set_states(task_id,state='WAITING_FOR_REMOTE',execution_state='SUCCEEDED' if conclusion=='CONFIRMED_APPLIED' else 'FAILED')
    def pending_outbox(self,task_id):return self.db.execute("SELECT * FROM messages WHERE task_id=? AND direction='OUT' AND delivered=0 ORDER BY message_id",(task_id,)).fetchall()
    def mark_delivered(self,message_id):
        with self.db:self.db.execute('UPDATE messages SET delivered=1 WHERE message_id=?',(message_id,))
