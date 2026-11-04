import pytest

from app.rga import ROOT, Id, Insert


def test_bigger_counter_wins():
    assert Id(5, "alice") > Id(4, "zed")


def test_same_counter_compares_replica():
    assert Id(4, "bob") > Id(4, "alice")


def test_ids_work_as_dict_keys():
    names = {Id(1, "a"): "x"}
    assert names[Id(1, "a")] == "x"


def test_rejects_non_ascii_replica():
    with pytest.raises(ValueError):
        Id(1, "é")


def test_insert_must_be_one_character():
    with pytest.raises(ValueError):
        Insert(Id(1, "a"), "ab", ROOT)