import json
from pathlib import Path

import pytest

from app.rga import Doc, op_from_json

SHARED = Path(__file__).resolve().parents[2] / "shared"


def load(file_name: str) -> list:
    return json.loads((SHARED / file_name).read_text())["cases"]


HAND = load("rga-cases.json")
RANDOM = load("rga-random.json")
CASES = HAND + RANDOM


def test_case_files_are_not_empty():
    assert HAND and RANDOM


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_shared_case(case):
    ops = [op_from_json(op) for op in case["ops"]]
    for order in (ops, list(reversed(ops))):
        doc = Doc("runner")
        for op in order:
            doc.apply(op)
        assert doc.text() == case["text"]
        assert doc.waiting == {}