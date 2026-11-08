
import sqlite3
from pathlib import Path

# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# File paths
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
DB_PATH = BASE_DIR / "database" / "returnable_assets.db"


def create_database():
    print("Starting database creation...")

    # Read SQL schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        schema_sql = file.read()

    # Connect to SQLite database
    connection = sqlite3.connect(DB_PATH)

    try:
        # Enable foreign key validation
        connection.execute("PRAGMA foreign_keys = ON;")

        # Execute all CREATE TABLE statements
        connection.executescript(schema_sql)
        connection.commit()

        print("\nDatabase created successfully!")
        print(f"Database location: {DB_PATH}")

        # Verify created tables
        cursor = connection.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
        """)

        tables = cursor.fetchall()

        print("\nCreated Tables:")
        for index, table in enumerate(tables, start=1):
            print(f"{index}. {table[0]}")

        print(f"\nTotal Tables: {len(tables)}")

        if len(tables) == 11:
            print("SUCCESS: All 11 tables created!")
        else:
            print("WARNING: Expected 11 tables.")

    except sqlite3.Error as error:
        print(f"Database Error: {error}")
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    create_database()
