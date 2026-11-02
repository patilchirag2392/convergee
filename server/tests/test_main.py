import pytest
from fastapi.testclient import TestClient

from app.main import app, documents


@pytest.fixture(autouse=True)
def fresh_documents():
    documents.clear()


def test_new_client_gets_empty_snapshot():
    client = TestClient(app)
    with client.websocket_connect("/ws/doc") as ws:
        assert ws.receive_json() == {"type": "snapshot", "text": ""}


def test_update_reaches_others_but_not_sender():
    client = TestClient(app)
    with client.websocket_connect("/ws/doc") as a, client.websocket_connect("/ws/doc") as b:
        a.receive_json()
        b.receive_json()

        a.send_json({"text": "hello"})
        assert b.receive_json() == {"type": "update", "text": "hello"}

        # If the server echoed "hello" back to a, it would be a's next message.
        b.send_json({"text": "world"})
        assert a.receive_json() == {"type": "update", "text": "world"}


def test_late_joiner_gets_latest_text():
    client = TestClient(app)
    with client.websocket_connect("/ws/doc") as a, client.websocket_connect("/ws/doc") as b:
        a.receive_json()
        b.receive_json()
        a.send_json({"text": "hello"})
        b.receive_json()  # wait until the server has actually processed the edit

        with client.websocket_connect("/ws/doc") as c:
            assert c.receive_json() == {"type": "snapshot", "text": "hello"}