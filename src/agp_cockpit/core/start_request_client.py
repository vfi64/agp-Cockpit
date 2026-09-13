from __future__ import annotations
import json,urllib.request
from agp_cockpit.adapters.macos_settings import bridge_token_path

def request_task_start(mission_id:str,*,base_url:str='http://127.0.0.1:9876')->dict:
    token=bridge_token_path().read_text(encoding='utf-8').strip()
    req=urllib.request.Request(base_url+'/v1/task/start-request',data=json.dumps({'mission_id':mission_id}).encode(),headers={'Content-Type':'application/json','X-AGP-Token':token},method='POST')
    with urllib.request.urlopen(req,timeout=5) as resp: return json.loads(resp.read().decode())
