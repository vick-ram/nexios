from typing import Any, Optional, Tuple, Sequence, Mapping, Iterable, List


def convert_row(row: Any) -> Optional[Tuple[Any, ...]]:
    """
    Convert any database row to tuple format

    Args:
        row: Raw row from any database driver
    Returns:
        Tuple representation or None if input is None
    """
    if row is None:
        return None

    if isinstance(row, tuple):
        return row

    if isinstance(row, Sequence) and not isinstance(row, (str, bytes)):
        return tuple(row)

    if hasattr(row, '_fields'):
        try:
            return tuple(row)
        except (TypeError, AttributeError):
            pass

    if isinstance(row, Mapping):
        return tuple(row.values())

    if hasattr(row, 'values') and callable(row.values): # type: ignore
        try:
            return tuple(row.values()) # type: ignore
        except (TypeError, AttributeError):
            pass

    if hasattr(row, '__iter__') and not isinstance(row, (str, bytes)):
        try:
            return tuple(iter(row))
        except (TypeError, StopIteration):
            pass

    return (row,)


def convert_rows(rows: Iterable[Any]) -> List[Tuple[Any, ...]]:
    """
    Convert multiple rows to list of tuples.

    Args:
        rows: Iterable of rows from database

    Returns:
        List of tuple representations
    """
    if rows is None:
        return []

    result = []
    for row in rows:
        converted = convert_row(row)
        if converted is not None:
            result.append(converted)
    return result