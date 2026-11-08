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
  if (id.counter < 1) throw new Error("a new character's counter must be >= 1");
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

type Item = {
  readonly id: Id;
  readonly value: string;
  readonly after: Id; // kept so we can rebuild this insert later
  deleted: boolean;
};

export class Doc {
  readonly replica: string;
  counter = 0; // highest counter seen so far (Lamport clock)
  readonly items: Item[] = []; // every character, in document order
  readonly byId = new Map<string, Item>(); // idKey -> character
  readonly waiting = new Map<string, Op[]>(); // idKey -> ops waiting for it

  constructor(replica: string) {
    if (!replica || !/^[\x00-\x7f]*$/.test(replica)) {
      throw new Error("replica must be a non-empty ASCII name");
    }
    this.replica = replica;
  }

  text(): string {
    return this.items
      .filter((item) => !item.deleted)
      .map((item) => item.value)
      .join("");
  }

  apply(op: Op): void {
    const queue: Op[] = [op];
    while (queue.length > 0) {
      const next = queue.pop() as Op;
      const need = this.missing(next);
      if (need !== null) {
        const key = idKey(need);
        const list = this.waiting.get(key);
        if (list) list.push(next);
        else this.waiting.set(key, [next]);
        continue;
      }
      if (next.type === "insert") {
        this.applyInsert(next);
        // Anyone waiting for this new character can go now.
        const key = idKey(next.id);
        const woken = this.waiting.get(key);
        if (woken) {
          this.waiting.delete(key);
          queue.push(...woken);
        }
      } else {
        this.applyDelete(next);
      }
    }
  }

  applyInsert(op: Insert): void {
    if (this.byId.has(idKey(op.id))) return; // same op arrived twice

    let i = this.indexAfter(op.after);
    // Step past characters that beat us: bigger siblings, and
    // anything typed after them (those always have bigger ids too).
    while (i < this.items.length && compareIds(this.items[i].id, op.id) > 0) {
      i++;
    }

    const item: Item = { id: op.id, value: op.value, after: op.after, deleted: false };
    this.items.splice(i, 0, item);
    this.byId.set(idKey(op.id), item);
    this.counter = Math.max(this.counter, op.id.counter);
  }

  applyDelete(op: Delete): void {
    const item = this.byId.get(idKey(op.target));
    if (!item) throw new Error("target not here yet");
    item.deleted = true; // hide it, but keep it: others may point at it
  }

    /** The user typed `value` at visible position `index` (in real characters). */
  localInsert(index: number, value: string): Insert {
    const after = this.idBefore(index);
    this.counter += 1;
    const op = makeInsert(makeId(this.counter, this.replica), value, after);
    this.apply(op);
    return op; // the caller sends this to everyone else
  }

  /** The user deleted the character at visible position `index`. */
  localDelete(index: number): Delete {
    const op: Delete = { type: "delete", target: this.visibleId(index) };
    this.apply(op);
    return op;
  }

    /** Name of the character just left of visible position `index` (ROOT at the start). */
  idBefore(index: number): Id {
    return index === 0 ? ROOT : this.visibleId(index - 1);
  }

  /** Visible position right after this character. If it's deleted, where it used to be. */
  positionAfter(id: Id): number {
    if (compareIds(id, ROOT) === 0) return 0;
    let visible = 0;
    for (const item of this.items) {
      if (!item.deleted) visible++;
      if (compareIds(item.id, id) === 0) return visible;
    }
    throw new Error("unknown character");
  }

  private visibleId(index: number): Id {
    if (index >= 0) {
      let seen = 0;
      for (const item of this.items) {
        if (!item.deleted) {
          if (seen === index) return item.id;
          seen++;
        }
      }
    }
    throw new RangeError("no visible character at that position");
  }

  private indexAfter(anchor: Id): number {
    if (compareIds(anchor, ROOT) === 0) return 0;
    if (!this.byId.has(idKey(anchor))) throw new Error("anchor not here yet");
    return this.items.findIndex((item) => compareIds(item.id, anchor) === 0) + 1;
  }

  private missing(op: Op): Id | null {
    const need = op.type === "insert" ? op.after : op.target;
    if (compareIds(need, ROOT) === 0 || this.byId.has(idKey(need))) return null;
    return need;
  }
}