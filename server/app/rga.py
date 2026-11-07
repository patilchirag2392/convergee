"""RGA sequence CRDT: character names and operations."""

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Id:
    """A character's permanent name. Bigger id goes first among siblings."""

    counter: int
    replica: str

    def __post_init__(self) -> None:
        if self.counter < 0:
            raise ValueError("counter must be >= 0")
        if not self.replica.isascii():
            raise ValueError("replica must be ASCII")


# The fake "start" character. Real ids start at counter 1, so nothing equals it.
ROOT = Id(0, "")


@dataclass(frozen=True)
class Insert:
    id: Id  # name of the new character
    value: str  # the character itself
    after: Id  # put it right after this one (ROOT = at the start)

    def __post_init__(self) -> None:
        if len(self.value) != 1:
            raise ValueError("insert exactly one character")


@dataclass(frozen=True)
class Delete:
    target: Id  # name of the character to hide


@dataclass
class Item:
    """One character in the document, including deleted ones."""

    id: Id
    value: str
    after: Id  # kept so we can rebuild this insert later (snapshots)
    deleted: bool = False


class Doc:
    def __init__(self, replica: str) -> None:
        self.replica = replica
        self.counter = 0  # highest counter seen so far (Lamport clock)
        self.items: list[Item] = []  # every character, in document order
        self.by_id: dict[Id, Item] = {}  # find a character by its name

    def text(self) -> str:
        return "".join(item.value for item in self.items if not item.deleted)

    def apply_insert(self, op: Insert) -> None:
        if op.id in self.by_id:
            return  # already have it: same op arrived twice

        i = self._index_after(op.after)

        # Step past characters that beat us: bigger siblings, and
        # anything typed after them (those always have bigger ids too).
        while i < len(self.items) and self.items[i].id > op.id:
            i += 1

        item = Item(op.id, op.value, op.after)
        self.items.insert(i, item)
        self.by_id[op.id] = item
        self.counter = max(self.counter, op.id.counter)

    def apply_delete(self, op: Delete) -> None:
        item = self.by_id.get(op.target)
        if item is None:
            raise ValueError("target not here yet")  # later: wait for it
        item.deleted = True  # hide it, but keep it: others may point at it

    def apply(self, op: Insert | Delete) -> None:
        if isinstance(op, Insert):
            self.apply_insert(op)
        else:
            self.apply_delete(op)

    def _index_after(self, anchor: Id) -> int:
        """List index right after the anchor character (0 for ROOT)."""
        if anchor == ROOT:
            return 0
        if anchor not in self.by_id:
            raise ValueError("anchor not here yet")  # later: wait for it
        for i, item in enumerate(self.items):
            if item.id == anchor:
                return i + 1
        raise AssertionError("by_id and items disagree")