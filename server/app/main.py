from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


@dataclass
class Document:
    text: str = ""
    clients: set[WebSocket] = field(default_factory=set)


# All state lives in this process's memory: gone on restart, invisible to other processes.
documents: dict[str, Document] = {}


@app.websocket("/ws/{doc_id}")
async def edit(websocket: WebSocket, doc_id: str) -> None:
    await websocket.accept()
    doc = documents.setdefault(doc_id, Document())
    doc.clients.add(websocket)
    try:
        await websocket.send_json({"type": "snapshot", "text": doc.text})
        while True:
            message = await websocket.receive_json()
            text = message["text"]
            doc.text = text  # last write wins: whatever arrives last overwrites everything
            for client in list(doc.clients):
                if client is websocket:
                    continue
                try:
                    await client.send_json({"type": "update", "text": text})
                except Exception:
                    # That peer is gone. Drop it, but don't let its failure end this sender's loop.
                    doc.clients.discard(client)
    except WebSocketDisconnect:
        pass
    finally:
        doc.clients.discard(websocket)