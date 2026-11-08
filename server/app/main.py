"""Converge server.

Each document is a room: the server's own RGA replica, plus the tabs
connected to it. Tabs send ops. The server checks them, applies them to
its copy, and forwards them to every other tab in the room.
"""

import json
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.rga import Delete, Doc, Insert, op_from_json, op_to_json

app = FastAPI()


@dataclass
class Room:
    doc: Doc = field(default_factory=lambda: Doc("server"))
    clients: set[WebSocket] = field(default_factory=set)


rooms: dict[str, Room] = {}


def parse_ops(text: str) -> list[Insert | Delete]:
    """Parse a whole message. Anything wrong raises ValueError."""
    message = json.loads(text)  # bad JSON raises JSONDecodeError, a kind of ValueError
    if not isinstance(message, dict) or message.get("type") != "ops":
        raise ValueError('expected {"type": "ops", "ops": [...]}')
    ops = message.get("ops")
    if not isinstance(ops, list):
        raise ValueError('"ops" must be a list')
    return [op_from_json(op) for op in ops]


@app.websocket("/ws/{doc_id}")
async def edit(websocket: WebSocket, doc_id: str) -> None:
    await websocket.accept()
    room = rooms.get(doc_id)
    if room is None:
        room = rooms[doc_id] = Room()

    # No await between taking the snapshot and joining the room,
    # so no op can land in the gap and be missed by this tab.
    snapshot = [op_to_json(op) for op in room.doc.snapshot_ops()]
    room.clients.add(websocket)

    try:
        await websocket.send_json({"type": "snapshot", "ops": snapshot})
        while True:
            text = await websocket.receive_text()
            try:
                ops = parse_ops(text)
            except ValueError as error:
                await websocket.send_json({"type": "error", "message": str(error)})
                continue

            for op in ops:
                room.doc.apply(op)

            out = {"type": "ops", "ops": [op_to_json(op) for op in ops]}
            for other in list(room.clients):
                if other is not websocket:
                    try:
                        await other.send_json(out)
                    except Exception:
                        room.clients.discard(other)  # that tab is already gone
    except WebSocketDisconnect:
        pass
    finally:
        room.clients.discard(websocket)