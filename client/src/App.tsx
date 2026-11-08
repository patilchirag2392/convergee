import { useEffect, useRef, useState } from "react";
import { Doc, opFromJson, opToJson, type Op } from "./rga";
import { diffText } from "./textDiff";

const SERVER = "ws://localhost:8000";

type Status = "connecting" | "live" | "disconnected";

/** JS string units -> real characters. */
function toChars(text: string, units: number): number {
  return Array.from(text.slice(0, units)).length;
}

/** Real characters -> JS string units. */
function toUnits(text: string, chars: number): number {
  return Array.from(text).slice(0, chars).join("").length;
}

/** Apply ops from others, keeping this tab's cursor where it was. */
function applyRemote(el: HTMLTextAreaElement, doc: Doc, ops: Op[]): void {
  // Remember the cursor by the names of the characters to its left.
  const startMark = doc.idBefore(toChars(el.value, el.selectionStart));
  const endMark = doc.idBefore(toChars(el.value, el.selectionEnd));
  for (const op of ops) doc.apply(op);
  el.value = doc.text();
  if (document.activeElement === el) {
    el.setSelectionRange(
      toUnits(el.value, doc.positionAfter(startMark)),
      toUnits(el.value, doc.positionAfter(endMark)),
    );
  }
}

export default function App() {
  const textarea = useRef<HTMLTextAreaElement>(null);
  const docRef = useRef<Doc | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<Status>("connecting");
  const name = window.location.pathname.slice(1) || "default";

  useEffect(() => {
    const doc = new Doc(crypto.randomUUID()); // fresh replica name every page load
    const socket = new WebSocket(`${SERVER}/ws/${encodeURIComponent(name)}`);
    docRef.current = doc;
    socketRef.current = socket;

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "error") {
        console.warn("server rejected an edit:", message.message);
        return;
      }
      const el = textarea.current;
      if (!el || (message.type !== "snapshot" && message.type !== "ops")) return;
      applyRemote(el, doc, message.ops.map(opFromJson));
      if (message.type === "snapshot") setStatus("live");
    };
    socket.onclose = () => setStatus("disconnected");

    return () => {
      // Detach first, so this old socket can't mark the new one as disconnected.
      socket.onmessage = null;
      socket.onclose = null;
      socket.close();
    };
  }, [name]);

  function handleInput(): void {
    const el = textarea.current;
    const doc = docRef.current;
    const socket = socketRef.current;
    if (!el || !doc || !socket) return;

    const edit = diffText(doc.text(), el.value, el.selectionEnd);
    const ops: Op[] = [];
    for (let k = 0; k < edit.deleteCount; k++) ops.push(doc.localDelete(edit.index));
    edit.insert.forEach((char, k) => ops.push(doc.localInsert(edit.index + k, char)));

    if (doc.text() !== el.value) console.error("doc and textarea disagree");
    if (ops.length > 0) socket.send(JSON.stringify({ type: "ops", ops: ops.map(opToJson) }));
  }

  return (
    <main>
      <p>
        Document: <strong>{name}</strong> · {status}
      </p>
      <textarea
        ref={textarea}
        onInput={handleInput}
        readOnly={status !== "live"}
        rows={20}
        cols={80}
      />
    </main>
  );
}