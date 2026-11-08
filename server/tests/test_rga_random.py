import random

import pytest

from app.rga import Doc


def random_session(seed: int, replicas: int = 3, steps: int = 200):
    rng = random.Random(seed)
    docs = [Doc(f"r{n}") for n in range(replicas)]
    log = []  # every op anyone made, in the order they were made
    for _ in range(steps):
        doc = rng.choice(docs)
        roll = rng.random()
        if roll < 0.4 and log:
            # Receive something: maybe old, maybe too early, maybe a repeat.
            doc.apply(rng.choice(log))
        elif roll < 0.8 or not doc.text():
            before = doc.text()
            index = rng.randint(0, len(before))
            char = rng.choice("abcdef")
            log.append(doc.local_insert(index, char))
            # The letter must show up exactly where it was typed.
            assert doc.text() == before[:index] + char + before[index:]
        else:
            before = doc.text()
            index = rng.randrange(len(before))
            log.append(doc.local_delete(index))
            # Exactly that one letter must disappear.
            assert doc.text() == before[:index] + before[index + 1:]
    return rng, docs, log


@pytest.mark.parametrize("seed", range(200))
def test_random_editing_converges(seed):
    rng, docs, log = random_session(seed)

    for doc in docs:
        deliveries = log + rng.sample(log, len(log) // 4)  # all ops, some twice
        rng.shuffle(deliveries)
        for op in deliveries:
            doc.apply(op)

    reference = Doc("ref")
    for op in log:
        reference.apply(op)

    for doc in docs:
        assert doc.text() == reference.text()
        assert doc.waiting == {}