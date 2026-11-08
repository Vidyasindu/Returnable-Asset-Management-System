import sqlite3
from pathlib import Path

DB_PATH = Path("database/returnable_assets.db")


def test_database_exists():
    assert DB_PATH.exists()


def test_database_connection():
    connection = sqlite3.connect(DB_PATH)
    assert connection is not None
    connection.close()


def test_foreign_key_integrity():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("PRAGMA foreign_key_check")
    errors = cursor.fetchall()

    connection.close()

    assert errors == []


def test_asset_record_count():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM ReusableAsset")
    count = cursor.fetchone()[0]

    connection.close()

    assert count == 20000