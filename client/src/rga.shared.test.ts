import { expect, test } from "vitest";
import handFile from "../../shared/rga-cases.json";
import randomFile from "../../shared/rga-random.json";
import { Doc, opFromJson } from "./rga";

type Case = { name: string; ops: unknown[]; text: string };
const hand: Case[] = handFile.cases;
const random: Case[] = randomFile.cases;

test("case files are not empty", () => {
  expect(hand.length).toBeGreaterThan(0);
  expect(random.length).toBeGreaterThan(0);
});

test.each([...hand, ...random])("$name", ({ ops, text }) => {
  const parsed = ops.map(opFromJson);
  for (const order of [parsed, [...parsed].reverse()]) {
    const doc = new Doc("runner");
    for (const op of order) doc.apply(op);
    expect(doc.text()).toBe(text);
    expect(doc.waiting.size).toBe(0);
  }
});