import pytest

from showads_client.validators import (
    InvalidAgeError,
    InvalidBannerIdError,
    InvalidCookieError,
    InvalidNameError,
    validate_age,
    validate_banner_id,
    validate_cookie,
    validate_name,
)


@pytest.mark.parametrize(
    "name,ok",
    [
        ("Alice", True),
        ("Ján Novak", True),
        ("Anna-Maria", False),
        ("  Peter  ", True),
        ("", False),
        ("   ", False),
        ("A1ice", False),
        ("Anne_", False),
        (None, False),
    ],
)
def test_validate_name(name, ok):
    if ok:
        assert validate_name(name) == str(name).strip()
    else:
        with pytest.raises(InvalidNameError):
            validate_name(name)


@pytest.mark.parametrize(
    "age,min_a,max_a,ok",
    [
        ("18", 18, 99, True),
        ("99", 18, 99, True),
        ("17", 18, 99, False),
        ("100", 18, 99, False),
        (" 25 ", 18, 99, True),
        ("25.0", 18, 99, False),
        ("xx", 18, 99, False),
        (None, 18, 99, False),
    ],
)
def test_validate_age(age, min_a, max_a, ok):
    if ok:
        assert validate_age(age, min_a, max_a) == int(str(age).strip())
    else:
        with pytest.raises(InvalidAgeError):
            validate_age(age, min_a, max_a)


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
def test_validate_banner_id(bid, ok):
    if ok:
        assert validate_banner_id(bid) == int(str(bid).strip())
    else:
        with pytest.raises(InvalidBannerIdError):
            validate_banner_id(bid)


@pytest.mark.parametrize(
    "cookie,ok",
    [
        ("00000000-0000-0000-0000-000000000001", True),
        ("not-a-uuid", False),
        ("", False),
        ("   ", False),
        (None, False),
    ],
)
def test_validate_cookie(cookie, ok):
    if ok:
        assert validate_cookie(cookie) == str(cookie)
    else:
        with pytest.raises(InvalidCookieError):
            validate_cookie(cookie)

