import pytest
from showads_client.validators import is_valid_name, is_valid_age, is_valid_banner_id


@pytest.mark.parametrize(
    "name,ok",
    [
        ("Alice", True),
        ("Ján Novak", True),  # unicode pismena/medzery
        ("Anna-Maria", True),  # hyphen povoleny
        ("  Peter  ", True),  # trim
        ("", False),
        ("   ", False),
        ("A1ice", False),  # cislice nie
        ("Anne_", False),  # znak '_' nie
        (None, False),
    ],
)
def test_is_valid_name(name, ok):
    assert is_valid_name(name) is ok


@pytest.mark.parametrize(
    "age,min_a,max_a,ok",
    [
        ("18", 18, 99, True),  # hranica min
        ("99", 18, 99, True),  # hranica max
        ("17", 18, 99, False),
        ("100", 18, 99, False),
        (" 25 ", 18, 99, True),  # trim + int()
        ("25.0", 18, 99, False),  # float string nie
        ("xx", 18, 99, False),
        (None, 18, 99, False),
    ],
)
def test_is_valid_age(age, min_a, max_a, ok):
    assert is_valid_age(age, min_a, max_a) is ok


@pytest.mark.parametrize(
    "bid,ok",
    [
        ("0", True),
        ("99", True),
        ("-1", False),
        ("100", False),
        (" 5 ", True),
        ("5.0", False),
        ("x", False),
        (None, False),
    ],
)
def test_is_valid_banner_id(bid, ok):
    assert is_valid_banner_id(bid) is ok
