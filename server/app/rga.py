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
        if not replica or not replica.isascii():
            raise ValueError("replica must be a non-empty ASCII name")
        self.replica = replica
        self.counter = 0  # highest counter seen so far (Lamport clock)
        self.items: list[Item] = []  # every character, in document order
        self.by_id: dict[Id, Item] = {}  # find a character by its name
        self.waiting: dict[Id, list[Insert | Delete]] = {}  # name -> ops waiting for it

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
        queue = [op]
        while queue:
            op = queue.pop()
            need = self._missing(op)
            if need is not None:
                self.waiting.setdefault(need, []).append(op)
                continue
            if isinstance(op, Insert):
                self.apply_insert(op)
                # Anyone waiting for this new character can go now.
                queue.extend(self.waiting.pop(op.id, []))
            else:
                self.apply_delete(op)

    def _missing(self, op: Insert | Delete) -> Id | None:
        """The name this op needs that we don't have yet, or None if ready."""
        need = op.after if isinstance(op, Insert) else op.target
        if need == ROOT or need in self.by_id:
            return None
        return need

    def local_insert(self, index: int, value: str) -> Insert:
        """The user typed `value` at visible position `index`."""
        after = ROOT if index == 0 else self._visible_id(index - 1)
        self.counter += 1
        op = Insert(Id(self.counter, self.replica), value, after)
        self.apply(op)
        return op  # the caller sends this to everyone else

    def local_delete(self, index: int) -> Delete:
        """The user deleted the character at visible position `index`."""
        op = Delete(self._visible_id(index))
        self.apply(op)
        return op

    def _visible_id(self, index: int) -> Id:
        """Name of the character the user sees at position `index`."""
        if index >= 0:
            seen = 0
            for item in self.items:
                if not item.deleted:
                    if seen == index:
                        return item.id
                    seen += 1
        raise IndexError("no visible character at that position")

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

def op_to_json(op: Insert | Delete) -> dict:
    if isinstance(op, Insert):
        return {
            "type": "insert",
            "id": _id_to_json(op.id),
            "value": op.value,
            "after": _id_to_json(op.after),
        }
    return {"type": "delete", "target": _id_to_json(op.target)}


def op_from_json(data: dict) -> Insert | Delete:
    if data["type"] == "insert":
        return Insert(
            _id_from_json(data["id"]), data["value"], _id_from_json(data["after"])
        )
    if data["type"] == "delete":
        return Delete(_id_from_json(data["target"]))
    raise ValueError(f"unknown op type: {data['type']!r}")


def _id_to_json(name: Id) -> list:
    return [name.counter, name.replica]


def _id_from_json(data) -> Id:
    if not (isinstance(data, list) and len(data) == 2):
        raise ValueError("id must be [counter, replica]")
    counter, replica = data
    if type(counter) is not int or type(replica) is not str:
        raise ValueError("id must be [int, str]")
    return Id(counter, replica)