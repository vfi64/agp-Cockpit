from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_protocol_freezes_file_transfer_boundary():
 d=(ROOT/'docs/planning/COMMUNICATION_PROTOCOL.md').read_text()
 s=(ROOT/'chrome_extension/content.js').read_text()
 assert 'K07 FILE_TRANSFER — NON-NEGOTIABLE ARCHITECTURE BOUNDARY' in d
 assert 'MUST NOT require, parse, repair, or execute a pure-JSON work order' in d
 g=s.index('K07_FILE_TRANSFER_ATTACHMENT_REQUIRED')
 j=s.index('const pureStructured = parsePureJsonObject(completed);',g)
 f=s.index('ASSISTANT_FORMAT_REPAIR',j)
 assert g < j < f
 assert 'submitAssistantCommandFile' in s and '/v1/file-loop/command' in s
