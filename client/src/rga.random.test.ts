import { expect, test } from "vitest";
import { Doc, type Op } from "./rga";

/** mulberry32: a small seeded random generator. Same seed, same numbers. */
function seededInt(seed: number): (n: number) => number {
  let state = seed | 0;
  const next = () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296; // 0 <= x < 1
  };
  return (n) => Math.floor(next() * n); // whole number from 0 to n - 1
}

function shuffle<T>(items: T[], int: (n: number) => number): void {
  for (let i = items.length - 1; i > 0; i--) {
    const j = int(i + 1);
    [items[i], items[j]] = [items[j], items[i]];
  }
}

const seeds = Array.from({ length: 100 }, (_, i) => i);

test.each(seeds)("random editing converges (seed %i)", (seed) => {
  const int = seededInt(seed);
  const docs = [0, 1, 2].map((n) => new Doc(`r${n}`));
  const log: Op[] = [];

  for (let step = 0; step < 200; step++) {
    const doc = docs[int(docs.length)];
    const roll = int(10);
    const before = doc.text();
    if (roll < 4 && log.length > 0) {
      doc.apply(log[int(log.length)]);
    } else if (roll < 8 || before === "") {
      const index = int(before.length + 1);
      const char = "abcdef"[int(6)];
      log.push(doc.localInsert(index, char));
      expect(doc.text()).toBe(before.slice(0, index) + char + before.slice(index));
    } else {
      const index = int(before.length);
      log.push(doc.localDelete(index));
      expect(doc.text()).toBe(before.slice(0, index) + before.slice(index + 1));
    }
  }

  for (const doc of docs) {
    const deliveries = [...log];
    for (let k = 0; k < log.length / 4; k++) deliveries.push(log[int(log.length)]);
    shuffle(deliveries, int);
    for (const op of deliveries) doc.apply(op);
  }

  const reference = new Doc("ref");
  for (const op of log) reference.apply(op);
  for (const doc of docs) {
    expect(doc.text()).toBe(reference.text());
    expect(doc.waiting.size).toBe(0);
  }
});