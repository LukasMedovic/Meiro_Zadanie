import pytest
from showads_client.batching import chunked


def test_chunked_basic():
    assert list(chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]


def test_chunked_size_gt_len():
    assert list(chunked([1, 2], 5)) == [[1, 2]]


def test_chunked_size_one():
    assert list(chunked([1, 2, 3], 1)) == [[1], [2], [3]]


def test_chunked_invalid_size():
    with pytest.raises(ValueError):
        list(chunked([1, 2], 0))
