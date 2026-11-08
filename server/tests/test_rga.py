import pytest
import itertools
import json

from app.rga import ROOT, Delete, Doc, Id, Insert, op_from_json, op_to_json


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

def two_replicas():
    alice, bob = Doc("alice"), Doc("bob")
    for op in abc():
        alice.apply(op)
        bob.apply(op)
    return alice, bob


def test_demo_case_1_now_converges():
    alice, bob = two_replicas()
    a_op = alice.local_insert(1, "X")
    b_op = bob.local_delete(2)  # Bob deletes "c"
    alice.apply(b_op)
    bob.apply(a_op)
    assert alice.text() == bob.text() == "aXb"


def test_demo_case_2_now_converges():
    alice, bob = two_replicas()
    a_op = alice.local_insert(1, "X")
    b_op = bob.local_insert(1, "Y")
    alice.apply(b_op)
    bob.apply(a_op)
    assert alice.text() == bob.text() == "aYXbc"


def test_local_typing_builds_a_chain():
    doc = Doc("me")
    first = doc.local_insert(0, "h")
    second = doc.local_insert(1, "i")
    assert doc.text() == "hi"
    assert first.id == Id(1, "me")
    assert second.after == first.id


def test_local_insert_counts_only_visible_characters():
    doc = Doc("me")
    for op in abc():
        doc.apply(op)
    doc.local_delete(1)  # hide "b", text is "ac"
    doc.local_insert(1, "X")  # between "a" and "c" on screen
    assert doc.text() == "aXc"


def test_new_name_beats_everything_seen():
    doc = Doc("me")
    doc.apply(ins(7, "s", "a"))
    op = doc.local_insert(1, "b")
    assert op.id == Id(8, "me")


def test_bad_positions_raise():
    doc = Doc("me")
    with pytest.raises(IndexError):
        doc.local_delete(0)  # nothing to delete
    with pytest.raises(IndexError):
        doc.local_insert(5, "x")  # past the end


def test_doc_needs_a_replica_name():
    with pytest.raises(ValueError):
        Doc("")

def test_insert_json_shape():
    op = ins(4, "alice", "X", after=Id(1, "s"))
    assert op_to_json(op) == {
        "type": "insert",
        "id": [4, "alice"],
        "value": "X",
        "after": [1, "s"],
    }

def test_delete_json_shape():
    assert op_to_json(Delete(Id(2, "s"))) == {"type": "delete", "target": [2, "s"]}


def test_root_json_shape():
    assert op_to_json(ins(1, "s", "a"))["after"] == [0, ""]


def test_ops_survive_a_round_trip():
    for op in abc() + [Delete(Id(2, "s"))]:
        text = json.dumps(op_to_json(op))
        assert op_from_json(json.loads(text)) == op


@pytest.mark.parametrize("bad", [[True, "a"], ["4", "a"], [4.0, "a"], [4], "4@a"])
def test_bad_ids_are_rejected(bad):
    with pytest.raises(ValueError):
        op_from_json({"type": "delete", "target": bad})


def test_unknown_op_type_is_rejected():
    with pytest.raises(ValueError):
        op_from_json({"type": "move"})

def test_counter_limit_matches_javascript():
    Id(2**53 - 1, "a")  # biggest allowed: fine
    with pytest.raises(ValueError):
        Id(2**53, "a")


def test_new_character_cannot_use_counter_zero():
    with pytest.raises(ValueError):
        Insert(Id(0, "a"), "x", ROOT)


@pytest.mark.parametrize(
    "junk",
    [
        None,
        [],
        {"type": "insert"},
        {"type": "insert", "id": [1, "a"], "value": 5, "after": [0, ""]},
        {"type": "delete"},
    ],
)
def test_junk_ops_raise_value_error(junk):
    with pytest.raises(ValueError):
        op_from_json(junk)


def test_snapshot_rebuilds_the_doc():
    doc = Doc("server")
    for op in abc() + [Delete(Id(2, "s")), ins(4, "bob", "X", after=Id(1, "s"))]:
        doc.apply(op)
    fresh = Doc("new-tab")
    for op in doc.snapshot_ops():
        fresh.apply(op)
        assert fresh.waiting == {}  # nothing in a snapshot has to wait
    assert fresh.text() == doc.text() == "aXc"
    assert [(i.id, i.deleted) for i in fresh.items] == [
        (i.id, i.deleted) for i in doc.items
    ]


def test_snapshot_includes_waiting_ops():
    doc = Doc("server")
    doc.apply(ins(2, "s", "b", after=Id(1, "s")))  # "a" hasn't arrived
    fresh = Doc("new-tab")
    for op in doc.snapshot_ops():
        fresh.apply(op)
    fresh.apply(ins(1, "s", "a"))
    assert fresh.text() == "ab"