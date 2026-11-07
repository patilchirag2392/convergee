import pytest
import itertools

from app.rga import ROOT, Delete, Doc, Id, Insert


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

def test_delete_hides_character():
    doc = Doc("me")
    for op in abc() + [Delete(Id(2, "s"))]:
        doc.apply(op)
    assert doc.text() == "ac"


def test_duplicate_delete_is_harmless():
    doc = Doc("me")
    for op in abc() + [Delete(Id(2, "s")), Delete(Id(2, "s"))]:
        doc.apply(op)
    assert doc.text() == "ac"


def test_insert_after_deleted_character():
    delete_b = Delete(Id(2, "s"))
    z = ins(4, "bob", "Z", after=Id(2, "s"))  # Bob types Z after b
    d1, d2 = Doc("alice"), Doc("bob")
    for op in abc() + [delete_b, z]:
        d1.apply(op)
    for op in abc() + [z, delete_b]:
        d2.apply(op)
    assert d1.text() == d2.text() == "aZc"

def test_insert_before_its_anchor_waits():
    doc = Doc("me")
    for op in reversed(abc()):  # c, then b, then a
        doc.apply(op)
    assert doc.text() == "abc"
    assert doc.waiting == {}


def test_delete_before_its_insert_waits():
    doc = Doc("me")
    for op in [Delete(Id(2, "s"))] + abc():
        doc.apply(op)
    assert doc.text() == "ac"
    assert doc.waiting == {}


def test_every_order_gives_the_same_text():
    ops = abc() + [
        ins(4, "alice", "X", after=Id(1, "s")),
        ins(4, "bob", "Y", after=Id(1, "s")),
        Delete(Id(2, "s")),
    ]
    for order in itertools.permutations(ops):  # all 720 orders
        doc = Doc("me")
        for op in order:
            doc.apply(op)
        assert doc.text() == "aYXc"
        assert doc.waiting == {}