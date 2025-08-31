from collections.abc import Iterable, Iterator
from typing import TypeVar

T = TypeVar("T")


def chunked(items: Iterable[T], size: int) -> Iterator[list[T]]:
    """Rozdeli vstupny iterovatelny zdroj na batch-e velkosti `size`.

    Vlastnosti:
      - Generator (pametovo setrne spracovanie aj pre velke kolekcie).
      - Zachovava poradie prvkov.
      - Posledny batch moze byt kratsi ako `size`.
      - Ak `size <= 0`, vyhodi ValueError (obrana proti chybnej konfiguracii).

    Priklady:
      list(chunked([1,2,3,4,5], 2)) -> [[1,2],[3,4],[5]]
    """
    if size <= 0:
        raise ValueError("size must be > 0")

    batch: list[T] = []
    for it in items:
        batch.append(it)
        if len(batch) >= size:
            # Vypustime plny batch a pripravime prazdny pre dalsie prvky
            yield batch
            batch = []
    if batch:
        # Vypustime posledny (neuplny) batch, ak ostal
        yield batch
