// RGA sequence CRDT, TypeScript version.
// Must behave exactly like server/app/rga.py. Shared tests in /shared check this.

export type Id = { readonly counter: number; readonly replica: string };

export type Insert = {
  readonly type: "insert";
  readonly id: Id; // name of the new character
  readonly value: string; // the character itself
  readonly after: Id; // put it right after this one (ROOT = at the start)
};

export type Delete = { readonly type: "delete"; readonly target: Id };

export type Op = Insert | Delete;

// The fake "start" character. Real ids start at counter 1.
export const ROOT: Id = { counter: 0, replica: "" };

export function makeId(counter: number, replica: string): Id {
  if (!Number.isSafeInteger(counter) || counter < 0) {
    throw new Error("counter must be a whole number >= 0");
  }
  if (!/^[\x00-\x7f]*$/.test(replica)) {
    throw new Error("replica must be ASCII");
  }
  return { counter, replica };
}

/** Negative if a < b, positive if a > b, 0 if equal. Same order as Python. */
export function compareIds(a: Id, b: Id): number {
  if (a.counter !== b.counter) return a.counter - b.counter;
  if (a.replica < b.replica) return -1;
  if (a.replica > b.replica) return 1;
  return 0;
}

/** A string unique to each id, so ids can be Map keys. */
export function idKey(id: Id): string {
  return `${id.counter}:${id.replica}`;
}

export function makeInsert(id: Id, value: string, after: Id): Insert {
  if ([...value].length !== 1) throw new Error("insert exactly one character");
  return { type: "insert", id, value, after };
}

export function opToJson(op: Op): unknown {
  if (op.type === "insert") {
    return {
      type: "insert",
      id: idToJson(op.id),
      value: op.value,
      after: idToJson(op.after),
    };
  }
  return { type: "delete", target: idToJson(op.target) };
}

export function opFromJson(data: unknown): Op {
  const d = data as Record<string, unknown> | null;
  if (d?.type === "insert") {
    if (typeof d.value !== "string") throw new Error("value must be a string");
    return makeInsert(idFromJson(d.id), d.value, idFromJson(d.after));
  }
  if (d?.type === "delete") {
    return { type: "delete", target: idFromJson(d.target) };
  }
  throw new Error(`unknown op type: ${String(d?.type)}`);
}

function idToJson(id: Id): [number, string] {
  return [id.counter, id.replica];
}

function idFromJson(data: unknown): Id {
  if (!Array.isArray(data) || data.length !== 2) {
    throw new Error("id must be [counter, replica]");
  }
  const [counter, replica] = data;
  if (typeof counter !== "number" || typeof replica !== "string") {
    throw new Error("id must be [number, string]");
  }
  return makeId(counter, replica);
}