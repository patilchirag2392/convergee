import { expect, test } from "vitest";
import { diffText } from "./textDiff";

test("typing in the middle", () => {
  expect(diffText("abc", "abXc", 3)).toEqual({ index: 2, deleteCount: 0, insert: ["X"] });
});

test("the cursor decides which of two equal letters is new", () => {
  // Typed "a" at the start of "aa": cursor ends up at 1.
  expect(diffText("aa", "aaa", 1)).toEqual({ index: 0, deleteCount: 0, insert: ["a"] });
  // Typed "a" at the end: cursor ends up at 3.
  expect(diffText("aa", "aaa", 3)).toEqual({ index: 2, deleteCount: 0, insert: ["a"] });
});

test("backspace removes the right one of two equal letters", () => {
  expect(diffText("aa", "a", 0)).toEqual({ index: 0, deleteCount: 1, insert: [] });
  expect(diffText("aa", "a", 1)).toEqual({ index: 1, deleteCount: 1, insert: [] });
});

test("deleting a selection", () => {
  expect(diffText("hello", "ho", 1)).toEqual({ index: 1, deleteCount: 3, insert: [] });
});

test("pasting over a selection", () => {
  expect(diffText("abc", "aXYc", 3)).toEqual({ index: 1, deleteCount: 1, insert: ["X", "Y"] });
});

test("an emoji counts as one character", () => {
  // "😀x" is 3 JS units long; the cursor after "x" is at 3.
  expect(diffText("😀", "😀x", 3)).toEqual({ index: 1, deleteCount: 0, insert: ["x"] });
});

test("no change gives an empty edit", () => {
  expect(diffText("abc", "abc", 1)).toEqual({ index: 1, deleteCount: 0, insert: [] });
});