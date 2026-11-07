import pytest

from app.rga import ROOT, Doc, Id, Insert


def test_bigger_counter_wins():
    assert Id(5, "alice") > Id(4, "zed")


def test_same_counter_compares_replica():
    assert Id(4, "bob") > Id(4, "alice")


def test_ids_work_as_dict_keys():
    names = {Id(1, "a"): "x"}
    assert names[Id(1, "a")] == "x"


def test_rejects_non_ascii_replica():
    with pytest.raises(ValueError):
        Id(1, "é")


def test_insert_must_be_one_character():
    with pytest.raises(ValueError):
        Insert(Id(1, "a"), "ab", ROOT)

def ins(counter, replica, value, after=ROOT):
    return Insert(Id(counter, replica), value, after)


def abc():
    """Ops that build "abc", typed by replica "s"."""
    return [
        ins(1, "s", "a"),
        ins(2, "s", "b", after=Id(1, "s")),
        ins(3, "s", "c", after=Id(2, "s")),
    ]


def test_typing_forward():
    doc = Doc("me")
    for op in abc():
        doc.apply_insert(op)
    assert doc.text() == "abc"


def test_newer_insert_at_start_goes_first():
    doc = Doc("me")
    doc.apply_insert(ins(1, "s", "b"))
    doc.apply_insert(ins(2, "s", "a"))  # also after ROOT, but newer
    assert doc.text() == "ab"


def test_same_spot_same_order_either_way():
    x = ins(4, "alice", "X", after=Id(1, "s"))
    y = ins(4, "bob", "Y", after=Id(1, "s"))
    d1, d2 = Doc("alice"), Doc("bob")
    for op in abc() + [x, y]:
        d1.apply_insert(op)
    for op in abc() + [y, x]:
        d2.apply_insert(op)
    assert d1.text() == d2.text() == "aYXbc"


def test_a_typed_word_stays_together():
    x = ins(4, "alice", "X", after=Id(1, "s"))
    y = ins(4, "bob", "Y", after=Id(1, "s"))
    z = ins(5, "bob", "Z", after=Id(4, "bob"))  # Bob typed Z after his Y
    d1, d2 = Doc("alice"), Doc("bob")
    for op in abc() + [x, y, z]:
        d1.apply_insert(op)
    for op in abc() + [y, z, x]:
        d2.apply_insert(op)
    assert d1.text() == d2.text() == "aYZXbc"


def test_duplicate_insert_is_ignored():
    doc = Doc("me")
    op = ins(1, "s", "a")
    doc.apply_insert(op)
    doc.apply_insert(op)
    assert doc.text() == "a"


def test_counter_jumps_to_highest_seen():
    doc = Doc("me")
    doc.apply_insert(ins(7, "s", "a"))
    assert doc.counter == 7