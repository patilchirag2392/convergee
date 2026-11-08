"""Why sending 'insert at index N' isn't enough.

Two replicas start from the same text, each makes one edit locally,
then each applies the other's edit. No server involved.
"""


def apply(text: str, op: dict) -> str:
    i = op["index"]
    if op["kind"] == "insert":
        return text[:i] + op["char"] + text[i:]
    if op["kind"] == "delete":
        return text[:i] + text[i + 1:]
    raise ValueError(op)


def run(name: str, start: str, alice_op: dict, bob_op: dict) -> None:
    alice = apply(start, alice_op)
    bob = apply(start, bob_op)
    alice = apply(alice, bob_op)  # Alice receives Bob's edit
    bob = apply(bob, alice_op)    # Bob receives Alice's edit
    result = "converged" if alice == bob else "DIVERGED"
    print(f"{name}: alice={alice!r} bob={bob!r} -> {result}")


# Case 1: Alice inserts before the char Bob deletes.
run("insert+delete", "abc",
    {"kind": "insert", "index": 1, "char": "X"},
    {"kind": "delete", "index": 2})  # Bob means: delete "c"

# Case 2: both insert at the same spot.
run("same spot", "abc",
    {"kind": "insert", "index": 1, "char": "X"},
    {"kind": "insert", "index": 1, "char": "Y"})