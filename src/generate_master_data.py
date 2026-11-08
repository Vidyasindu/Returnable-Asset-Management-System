
import sqlite3
import random
import pandas as pd

from datetime import date
from faker import Faker

from config import (
    DB_PATH,
    RAW_DATA_DIR,
    RANDOM_SEED,
    TOTAL_ASSETS
)


# ==========================================
# INITIALIZE RANDOM GENERATORS
# ==========================================

rng = random.Random(RANDOM_SEED)

fake = Faker()
fake.seed_instance(RANDOM_SEED)


# ==========================================
# 1. GENERATE ASSET TYPES
# ==========================================

def generate_asset_types():

    asset_types = [
        ("AT001", "Plastic Box", 15, 500.00, 1),
        ("AT002", "Wooden Pallet", 30, 1000.00, 1),
        ("AT003", "Metal Container", 45, 2000.00, 1),
        ("AT004", "Industrial Crate", 20, 1500.00, 1),
        ("AT005", "Reusable Drum", 25, 800.00, 0)
    ]

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")

        current_time = "2026-11-07T09:00:00"

        records = [
            (*asset, current_time)
            for asset in asset_types
        ]

        connection.executemany(
            """
            INSERT OR IGNORE INTO AssetType
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records
        )

        connection.commit()

        print("AssetType records:", len(asset_types))

    finally:
        connection.close()


# ==========================================
# 2. GENERATE OWNERS
# ==========================================

def generate_owners():

    owners = [
        ("OWN001", "ABC Packaging Ltd", "SUPPLIER", "abc@example.com"),
        ("OWN002", "XYZ Manufacturing", "CUSTOMER", "xyz@example.com"),
        ("OWN003", "FastTrack Logistics", "LOGISTICS", "fasttrack@example.com"),
        ("OWN004", "Global Packaging Solutions", "SUPPLIER", "global@example.com"),
        ("OWN005", "Hyderabad Retail Pvt Ltd", "CUSTOMER", "retail@example.com"),
        ("OWN006", "Speed Cargo Services", "LOGISTICS", "speed@example.com"),
        ("OWN007", "Prime Industrial Supplies", "SUPPLIER", "prime@example.com"),
        ("OWN008", "Metro Distribution Ltd", "CUSTOMER", "metro@example.com"),
        ("OWN009", "Reliable Transport Co", "LOGISTICS", "reliable@example.com"),
        ("OWN010", "Universal Packaging", "SUPPLIER", "universal@example.com")
    ]

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")

        current_time = "2026-11-07T09:00:00"

        records = [
            (*owner, current_time)
            for owner in owners
        ]

        connection.executemany(
            """
            INSERT OR IGNORE INTO Owner
            VALUES (?, ?, ?, ?, ?)
            """,
            records
        )

        connection.commit()

        print("Owner records:", len(owners))

    finally:
        connection.close()


# ==========================================
# 3. GENERATE LOCATIONS
# ==========================================

def generate_locations():

    locations = [
        ("LOC001", "Hyderabad Warehouse", "WAREHOUSE", "Hyderabad", "Telangana"),
        ("LOC002", "Chennai Warehouse", "WAREHOUSE", "Chennai", "Tamil Nadu"),
        ("LOC003", "Bangalore Warehouse", "WAREHOUSE", "Bangalore", "Karnataka"),
        ("LOC004", "Mumbai Warehouse", "WAREHOUSE", "Mumbai", "Maharashtra"),
        ("LOC005", "ABC Supplier Location", "SUPPLIER", "Hyderabad", "Telangana"),
        ("LOC006", "XYZ Customer Location", "CUSTOMER", "Chennai", "Tamil Nadu"),
        ("LOC007", "Pune Customer Location", "CUSTOMER", "Pune", "Maharashtra"),
        ("LOC008", "Delhi Customer Location", "CUSTOMER", "Delhi", "Delhi"),
        ("LOC009", "Hyderabad Repair Centre", "REPAIR_CENTER", "Hyderabad", "Telangana"),
        ("LOC010", "Bangalore Repair Centre", "REPAIR_CENTER", "Bangalore", "Karnataka")
    ]

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")

        current_time = "2026-11-07T09:00:00"

        records = [
            (*location, current_time)
            for location in locations
        ]

        connection.executemany(
            """
            INSERT OR IGNORE INTO Location
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            records
        )

        connection.commit()

        print("Location records:", len(locations))

    finally:
        connection.close()


# ==========================================
# 4. GENERATE REUSABLE ASSETS
# ==========================================

def generate_reusable_assets():

    print("\nGenerating reusable assets...")

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")

        cursor = connection.cursor()

        # Fetch asset types
        cursor.execute("""
            SELECT asset_type_id, deposit_amount
            FROM AssetType
        """)

        asset_types = cursor.fetchall()

        # Fetch suppliers
        cursor.execute("""
            SELECT owner_id
            FROM Owner
            WHERE owner_type = 'SUPPLIER'
        """)

        owners = [row[0] for row in cursor.fetchall()]

        # Fetch warehouse locations
        cursor.execute("""
            SELECT location_id
            FROM Location
            WHERE location_type = 'WAREHOUSE'
        """)

        locations = [row[0] for row in cursor.fetchall()]

        if not asset_types or not owners or not locations:
            raise ValueError("Master data is missing!")

        records = []

        for i in range(1, TOTAL_ASSETS + 1):

            asset_type_id, deposit_amount = rng.choice(asset_types)

            owner_id = rng.choice(owners)

            location_id = rng.choice(locations)

            purchase_date = fake.date_between(
                start_date=date(2023, 1, 1),
                end_date=date(2026, 10, 31)
            )

            asset = (
                f"ASSET-{i:07d}",
                asset_type_id,
                owner_id,
                location_id,
                "AVAILABLE",
                purchase_date.isoformat(),
                deposit_amount,
                purchase_date.isoformat() + "T09:00:00"
            )

            records.append(asset)

        # Convert to DataFrame
        columns = [
            "asset_id",
            "asset_type_id",
            "owner_id",
            "current_location_id",
            "asset_status",
            "purchase_date",
            "deposit_amount",
            "created_at"
        ]

        df = pd.DataFrame(records, columns=columns)

        # Export CSV
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

        csv_path = RAW_DATA_DIR / "reusable_assets.csv"

        df.to_csv(csv_path, index=False)

        # Insert into database
        connection.executemany(
            """
            INSERT INTO ReusableAsset (
                asset_id,
                asset_type_id,
                owner_id,
                current_location_id,
                asset_status,
                purchase_date,
                deposit_amount,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                asset_type_id = excluded.asset_type_id,
                owner_id = excluded.owner_id,
                current_location_id = excluded.current_location_id,
                asset_status = excluded.asset_status,
                purchase_date = excluded.purchase_date,
                deposit_amount = excluded.deposit_amount,
                created_at = excluded.created_at
            """,
            records
        )

        connection.commit()

        print("\nReusable assets generated successfully!")

        print("Total assets:", len(df))

        print(
            "Unique asset IDs:",
            df["asset_id"].nunique()
        )

        print("\nSample records:")

        print(df.head(5).to_string(index=False))

        print("\nAsset status distribution:")

        print(df["asset_status"].value_counts())

        print("\nCSV saved at:", csv_path)

    except Exception as error:

        connection.rollback()

        print("Error:", error)

        raise

    finally:

        connection.close()


# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == "__main__":

    print("Starting Master Data Generation...\n")

    generate_asset_types()

    generate_owners()

    generate_locations()

    generate_reusable_assets()

    print("\nAll master data generated successfully!")
