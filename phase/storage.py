from contextlib import contextmanager
from os import PathLike
import sqlite3
from typing import Iterator


def connect(path: str | PathLike[str]) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def initialize(connection: sqlite3.Connection, schema: str) -> None:
    if connection.in_transaction:
        raise RuntimeError('initialize outside a write transaction')
    connection.execute('PRAGMA foreign_keys = ON')
    connection.executescript(schema)


@contextmanager
def write_transaction(connection: sqlite3.Connection) -> Iterator[None]:
    connection.execute('BEGIN IMMEDIATE')
    try:
        yield
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
