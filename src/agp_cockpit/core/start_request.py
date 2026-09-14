from __future__ import annotations
import json
from pathlib import Path

class StartRequestStore:
    def __init__(self,root:Path)->None:
        self.path=root/'task_start_request.json'; self.path.parent.mkdir(parents=True,exist_ok=True)
    def _read(self)->dict:
        try: return json.loads(self.path.read_text(encoding='utf-8'))
        except (FileNotFoundError,json.JSONDecodeError): return {'generation':0,'mission_id':'','task_id':''}
    def request(self,mission_id:str,*,task_id:str='')->dict:
        cur=self._read(); data={
            'generation':int(cur.get('generation',0))+1,
            'mission_id':str(mission_id),
            'task_id':str(task_id),
        }
        tmp=self.path.with_suffix('.tmp'); tmp.write_text(json.dumps(data)+'\n',encoding='utf-8'); tmp.replace(self.path); return data
    def current(self)->dict: return self._read()
