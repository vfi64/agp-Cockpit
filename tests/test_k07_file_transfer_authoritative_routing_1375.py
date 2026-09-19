from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_normal_k07_requires_attachment_before_legacy_json():
 s=(ROOT/'chrome_extension/content.js').read_text()
 a=s.index('K07_FILE_TRANSFER_ATTACHMENT_REQUIRED')
 b=s.index('const pureStructured = parsePureJsonObject(completed);',a)
 assert a < b
 assert 'submitAssistantCommandFile' in s
 assert '/v1/file-loop/command' in s
 assert 'Do not return Protocol-v1 JSON for a normal task-first K07 cycle.' in s
