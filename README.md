# Converge

A real-time collaborative plain-text editor. Multiple people edit the same
document at once, and every replica converges to identical text.

This is a learning project. The sync and conflict-resolution logic is written
from scratch: no Yjs, Automerge, ShareDB, or any library that does the merging.

## Stack

- Client: React + TypeScript (Vite)
- Server: Python + FastAPI, WebSockets

## Layout

- `server/`: FastAPI app and tests
- `client/`: React app and tests

## How to run

Server (from `server/`):

```bash
uv sync
uv run uvicorn app.main:app
```

Client (from `client/`):

```bash
npm install
npm run dev
```

Open http://localhost:5173/notes in two tabs. The part after `/` is the document name.

Tests (from `server/`): `uv run pytest`

Lost-update demo (from `server/`, with the server running):
`uv run python scripts/lost_update.py`

## Progress

- [x] Stage 0: last-write-wins baseline, reproduce the lost update
- [ ] Stage 1: custom sequence CRDT
- [ ] Stage 2: persistence with PostgreSQL
- [ ] Stage 3: two instances, Redis pub/sub
- [ ] Stage 4: Docker and CI
- [ ] Stage 5: deploy to AWS