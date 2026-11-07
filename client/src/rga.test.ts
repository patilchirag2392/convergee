import { expect, test } from "vitest";
import {
  ROOT,
  compareIds,
  idKey,
  makeId,
  makeInsert,
  opFromJson,
  opToJson,
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