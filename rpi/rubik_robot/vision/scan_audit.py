"""Record the actual saved scan and solver input for color-mismatch diagnosis."""
import json
from pathlib import Path


AUDIT_DIRECTORY = Path(__file__).resolve().parents[3] / 'calibration'


def write_audit(name, payload, directory=None):
    folder = AUDIT_DIRECTORY if directory is None else Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (name + '.json')
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(target)
