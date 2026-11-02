import { useEffect, useRef, useState, type ChangeEvent } from "react";

const SERVER = "ws://localhost:8000/ws";

// localhost:5173/notes  ->  document "notes"
const docId = window.location.pathname.slice(1) || "default";

export default function App() {
  const [text, setText] = useState("");
  const [status, setStatus] = useState("connecting");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(`${SERVER}/${encodeURIComponent(docId)}`);
    socketRef.current = socket;

    socket.onopen = () => setStatus("connected");
    socket.onclose = () => setStatus("disconnected");
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      // Snapshot or update: either way, the server's text replaces ours.
      setText(message.text);
    };

    return () => {
      // Unhook first, so this old socket can't change the page after it's gone.
      socket.onopen = null;
      socket.onclose = null;
      socket.onmessage = null;
      socket.close();
    };
  }, []);

  function handleChange(event: ChangeEvent<HTMLTextAreaElement>) {
    const newText = event.target.value;
    setText(newText);
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ text: newText }));
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: "2rem auto", fontFamily: "system-ui" }}>
      <h1>Converge</h1>
      <p>
        document: <b>{docId}</b> · {status}
      </p>
      <textarea
        value={text}
        onChange={handleChange}
        rows={20}
        style={{ width: "100%", fontSize: 16 }}
      />
    </main>
  );
}