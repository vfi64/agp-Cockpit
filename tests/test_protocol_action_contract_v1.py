from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def test_browser_action_contract_disambiguates_ui_from_protocol_mode():
 t=(ROOT/'chrome_extension/protocol_action_contract_v1.js').read_text()
 assert 'ACTION_MODES=Object.freeze(["DIRECT_EXECUTION","FILE_TRANSFER"])' in t
 assert 'COPY_PASTE is legacy/UI communication terminology' in t
 assert 'MUST NEVER be emitted as Protocol-v1 action.mode' in t
 assert 'Do not invent, alias, translate, infer, or repair mode values.' in t

def test_strict_protocol_modes_remain_unchanged():
 js=(ROOT/'chrome_extension/transport_protocol_v1.js').read_text()
 py=(ROOT/'src/agp_cockpit/core/transport_protocol_v1.py').read_text()
 assert 'new Set(["DIRECT_EXECUTION","FILE_TRANSFER"])' in js
 assert 'VALID_MODES=frozenset({"DIRECT_EXECUTION","FILE_TRANSFER"})' in py
 assert 'COPY_PASTE' not in js
 assert 'COPY_PASTE' not in py

def test_contract_loaded_before_strict_protocol_parser():
 m=json.loads((ROOT/'chrome_extension/manifest.json').read_text())
 lists=[x.get('js',[]) for x in m.get('content_scripts',[]) if 'transport_protocol_v1.js' in x.get('js',[])]
 assert lists
 for js in lists:
  assert 'protocol_action_contract_v1.js' in js
  assert js.index('protocol_action_contract_v1.js') < js.index('transport_protocol_v1.js')
