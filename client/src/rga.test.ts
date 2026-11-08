import { expect, test } from "vitest";
import {
  ROOT,
  compareIds,
  idKey,
  makeId,
  makeInsert,
  opFromJson,
  opToJson,
  Doc,
} from "./rga";

test("bigger counter wins", () => {
  expect(compareIds(makeId(5, "alice"), makeId(4, "zed"))).toBeGreaterThan(0);
});

test("same counter compares replica", () => {
  expect(compareIds(makeId(4, "bob"), makeId(4, "alice"))).toBeGreaterThan(0);
});

test("uppercase sorts before lowercase, like Python", () => {
  expect(compareIds(makeId(4, "alice"), makeId(4, "Bob"))).toBeGreaterThan(0);
});

test("names compare as text, not numbers", () => {
  expect(compareIds(makeId(4, "r9"), makeId(4, "r10"))).toBeGreaterThan(0);
});

test("equal ids compare as 0 and share a key", () => {
  expect(compareIds(makeId(1, "a"), makeId(1, "a"))).toBe(0);
  expect(idKey(makeId(1, "a"))).toBe(idKey(makeId(1, "a")));
});

test("rejects non-ASCII replica", () => {
  expect(() => makeId(1, "é")).toThrow();
});

test("insert must be one character, and an emoji counts as one", () => {
  expect(() => makeInsert(makeId(1, "a"), "ab", ROOT)).toThrow();
  expect(makeInsert(makeId(1, "a"), "😀", ROOT).value).toBe("😀");
});

test("ops survive a JSON round trip", () => {
  const json = { type: "insert", id: [4, "alice"], value: "X", after: [1, "s"] };
  expect(opToJson(opFromJson(JSON.parse(JSON.stringify(json))))).toEqual(json);
});

test.each([[[true, "a"]], [["4", "a"]], [[4.5, "a"]], [[4]], ["4@a"]])(
  "rejects bad id %j",
  (bad) => {
    expect(() => opFromJson({ type: "delete", target: bad })).toThrow();
  },
);

test("rejects unknown op type", () => {
  expect(() => opFromJson({ type: "move" })).toThrow();
});

function abcDoc(replica: string): Doc {
  const s = (n: number) => makeId(n, "s");
  const doc = new Doc(replica);
  doc.apply(makeInsert(s(1), "a", ROOT));
  doc.apply(makeInsert(s(2), "b", s(1)));
  doc.apply(makeInsert(s(3), "c", s(2)));
  return doc;
}

test("demo case 1 now converges", () => {
  const alice = abcDoc("alice");
  const bob = abcDoc("bob");
  const a = alice.localInsert(1, "X");
  const b = bob.localDelete(2); // Bob deletes "c"
  alice.apply(b);
  bob.apply(a);
  expect(alice.text()).toBe("aXb");
  expect(bob.text()).toBe("aXb");
});

test("demo case 2 now converges", () => {
  const alice = abcDoc("alice");
  const bob = abcDoc("bob");
  const a = alice.localInsert(1, "X");
  const b = bob.localInsert(1, "Y");
  alice.apply(b);
  bob.apply(a);
  expect(alice.text()).toBe("aYXbc");
  expect(bob.text()).toBe("aYXbc");
});

test("local typing builds a chain", () => {
  const doc = new Doc("me");
  const first = doc.localInsert(0, "h");
  const second = doc.localInsert(1, "i");
  expect(doc.text()).toBe("hi");
  expect(first.id).toEqual(makeId(1, "me"));
  expect(second.after).toEqual(first.id);
});

test("local insert counts only visible characters", () => {
  const doc = abcDoc("me");
  doc.localDelete(1); // hide "b", text is "ac"
  doc.localInsert(1, "X"); // between "a" and "c" on screen
  expect(doc.text()).toBe("aXc");
});

test("new name beats everything seen", () => {
  const doc = new Doc("me");
  doc.apply(makeInsert(makeId(7, "s"), "a", ROOT));
  expect(doc.localInsert(1, "b").id).toEqual(makeId(8, "me"));
});

test("positions count an emoji as one character", () => {
  const doc = new Doc("me");
  doc.localInsert(0, "😀");
  doc.localInsert(1, "x"); // position 1 is right after the emoji
  expect(doc.text()).toBe("😀x");
});

test("bad positions throw", () => {
  const doc = new Doc("me");
  expect(() => doc.localDelete(0)).toThrow(RangeError);
  expect(() => doc.localInsert(5, "x")).toThrow(RangeError);
});

test("doc needs a replica name", () => {
  expect(() => new Doc("")).toThrow();
});

test("new character cannot use counter zero", () => {
  expect(() => makeInsert(makeId(0, "a"), "x", ROOT)).toThrow();
});

test("remote insert before the cursor pushes it right", () => {
  const doc = abcDoc("me");
  const mark = doc.idBefore(2); // cursor between "b" and "c"
  doc.apply(makeInsert(makeId(4, "bob"), "X", makeId(1, "s"))); // "aXbc"
  expect(doc.positionAfter(mark)).toBe(3);
});

test("remote insert after the cursor leaves it alone", () => {
  const doc = abcDoc("me");
  const mark = doc.idBefore(1); // cursor between "a" and "b"
  doc.apply(makeInsert(makeId(4, "bob"), "Y", makeId(2, "s"))); // "abYc"
  expect(doc.positionAfter(mark)).toBe(1);
});

test("remote insert right at the cursor goes after it", () => {
  const doc = abcDoc("me");
  const mark = doc.idBefore(1); // cursor right after "a"
  doc.apply(makeInsert(makeId(4, "bob"), "X", makeId(1, "s"))); // "aXbc"
  expect(doc.positionAfter(mark)).toBe(1); // still right after "a"
});

test("if the character left of the cursor is deleted, the cursor stays put", () => {
  const doc = abcDoc("me");
  const mark = doc.idBefore(2); // cursor right after "b"
  doc.apply({ type: "delete", target: makeId(2, "s") }); // "ac"
  expect(doc.positionAfter(mark)).toBe(1); // between "a" and "c"
});

test("cursor at the very start stays at the start", () => {
  const doc = abcDoc("me");
  const mark = doc.idBefore(0);
  doc.apply(makeInsert(makeId(4, "bob"), "X", makeId(3, "s"))); // "abcX"
  expect(doc.positionAfter(mark)).toBe(0);
});