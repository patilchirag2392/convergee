import pytest
from fastapi.testclient import TestClient
from app.rga import Doc, op_from_json, op_to_json

from app.main import app, rooms

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_rooms():
    rooms.clear()  # every test starts with no documents


def insert(counter, replica, value, after=(0, "")):
    return {"type": "insert", "id": [counter, replica], "value": value, "after": list(after)}


def ops_message(*ops):
    return {"type": "ops", "ops": list(ops)}


def test_new_doc_sends_an_empty_snapshot():
    with client.websocket_connect("/ws/notes") as alice:
        assert alice.receive_json() == {"type": "snapshot", "ops": []}


def test_ops_reach_others_but_not_the_sender():
    with client.websocket_connect("/ws/notes") as alice, client.websocket_connect(
        "/ws/notes"
    ) as bob:
        alice.receive_json()  # snapshots
        bob.receive_json()
        a = insert(1, "alice", "a")
        alice.send_json(ops_message(a))
        assert bob.receive_json() == ops_message(a)

        b = insert(2, "bob", "b", after=(1, "alice"))
        bob.send_json(ops_message(b))
        # If Alice had been sent her own op, it would arrive first.
        assert alice.receive_json() == ops_message(b)


def test_late_joiner_gets_every_character_including_tombstones():
    a = insert(1, "alice", "a")
    b = insert(2, "alice", "b", after=(1, "alice"))
    delete_b = {"type": "delete", "target": [2, "alice"]}
    with client.websocket_connect("/ws/notes") as alice, client.websocket_connect(
        "/ws/notes"
    ) as bob:
        alice.receive_json()
        bob.receive_json()
        alice.send_json(ops_message(a, b, delete_b))
        bob.receive_json()  # once Bob has it, the server has applied it

        assert rooms["notes"].doc.text() == "a"  # the server is a real replica
        with client.websocket_connect("/ws/notes") as carol:
            assert carol.receive_json() == {"type": "snapshot", "ops": [a, b, delete_b]}


def test_bad_message_gets_an_error_and_the_connection_stays_open():
    with client.websocket_connect("/ws/notes") as alice, client.websocket_connect(
        "/ws/notes"
    ) as bob:
        alice.receive_json()
        bob.receive_json()
        alice.send_text("not json")
        assert alice.receive_json()["type"] == "error"

        a = insert(1, "alice", "a")
        alice.send_json(ops_message(a))
        assert bob.receive_json() == ops_message(a)


def test_one_bad_op_rejects_the_whole_message():
    with client.websocket_connect("/ws/notes") as alice:
        alice.receive_json()
        alice.send_json(ops_message(insert(1, "alice", "a"), {"type": "insert"}))
        assert alice.receive_json()["type"] == "error"
        assert rooms["notes"].doc.text() == ""  # the good op wasn't applied either

def receive_into(ws, doc):
    """Apply every op in the next message (snapshot or ops) to a local Doc."""
    for op in ws.receive_json()["ops"]:
        doc.apply(op_from_json(op))


def send_ops(ws, ops):
    ws.send_json(ops_message(*[op_to_json(op) for op in ops]))


def test_concurrent_edits_through_the_server_converge():
    with client.websocket_connect("/ws/notes") as alice_ws, client.websocket_connect(
        "/ws/notes"
    ) as bob_ws:
        alice, bob = Doc("alice"), Doc("bob")
        receive_into(alice_ws, alice)  # snapshots
        receive_into(bob_ws, bob)

        # Alice types "abc", and Bob receives it.
        send_ops(alice_ws, [alice.local_insert(i, ch) for i, ch in enumerate("abc")])
        receive_into(bob_ws, bob)

        # Now both edit at once, before seeing each other's edit.
        send_ops(alice_ws, [alice.local_insert(1, "X")])  # "aXbc"
        send_ops(bob_ws, [bob.local_delete(2), bob.local_insert(1, "Y")])  # "aYb"
        receive_into(alice_ws, alice)
        receive_into(bob_ws, bob)

        assert alice.text() == bob.text() == rooms["notes"].doc.text() == "aYXb"