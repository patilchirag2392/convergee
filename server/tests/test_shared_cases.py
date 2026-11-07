import json
from pathlib import Path

import pytest

from app.rga import Doc, op_from_json

# server/tests/this_file.py -> up two folders is the repo root
CASES_FILE = Path(__file__).resolve().parents[2] / "shared" / "rga-cases.json"
CASES = json.loads(CASES_FILE.read_text())["cases"]


def test_cases_file_is_not_empty():
    assert CASES


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_shared_case(case):
    ops = [op_from_json(op) for op in case["ops"]]
    for order in (ops, list(reversed(ops))):
        doc = Doc("runner")
        for op in order:
            doc.apply(op)
        assert doc.text() == case["text"]
        assert doc.waiting == {}