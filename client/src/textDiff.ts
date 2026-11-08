/** One connected change, counted in real characters (an emoji is 1). */
export type Edit = { index: number; deleteCount: number; insert: string[] };

/**
 * Work out what changed between two versions of the textarea's text.
 * `cursor` is where the caret is in `after`, in JS string units
 * (what textarea.selectionEnd gives you).
 */
export function diffText(before: string, after: string, cursor: number): Edit {
  const old = Array.from(before); // real characters
  const now = Array.from(after);
  const caret = Array.from(after.slice(0, cursor)).length; // JS units -> real characters

  // Everything after the caret was untouched, so match the end first, up to the caret.
  let suffix = 0;
  const maxSuffix = Math.min(now.length - caret, old.length);
  while (suffix < maxSuffix && old[old.length - 1 - suffix] === now[now.length - 1 - suffix]) {
    suffix++;
  }

  // Then match the start, without overlapping the matched end.
  let prefix = 0;
  const maxPrefix = Math.min(old.length, now.length) - suffix;
  while (prefix < maxPrefix && old[prefix] === now[prefix]) {
    prefix++;
  }

  return {
    index: prefix,
    deleteCount: old.length - suffix - prefix,
    insert: now.slice(prefix, now.length - suffix),
  };
}