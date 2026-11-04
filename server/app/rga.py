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