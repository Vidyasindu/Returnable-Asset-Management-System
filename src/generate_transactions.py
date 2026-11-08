
import sqlite3
import random
import pandas as pd

from datetime import datetime, timedelta

from config import (
    DB_PATH,
    RAW_DATA_DIR,
    RANDOM_SEED,
    TOTAL_SHIPMENTS
)


def generate_shipments():

    print("\nStarting Corrected Shipment Generation...")

    rng = random.Random(RANDOM_SEED)

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        cursor = connection.cursor()

        # 1. Fetch customer locations
        cursor.execute("""
            SELECT location_id
            FROM Location
            WHERE location_type = 'CUSTOMER'
        """)
        customers = [row[0] for row in cursor.fetchall()]

        # 2. Fetch logistics carriers
        cursor.execute("""
            SELECT owner_id
            FROM Owner
            WHERE owner_type = 'LOGISTICS'
        """)
        carriers = [row[0] for row in cursor.fetchall()]

        # 3. Fetch assets and their current warehouse locations
        cursor.execute("""
            SELECT asset_id, current_location_id
            FROM ReusableAsset
            ORDER BY asset_id
        """)

        asset_rows = cursor.fetchall()

        if not asset_rows or not customers or not carriers:
            raise ValueError("Required master data is missing!")

        # 4. Group assets by warehouse
        assets_by_location = {}

        for asset_id, location_id in asset_rows:

            if location_id is None:
                raise ValueError(
                    f"Asset {asset_id} has no current location!"
                )

            assets_by_location.setdefault(
                location_id, []
            ).append(asset_id)

        total_assets = sum(
            len(asset_list)
            for asset_list in assets_by_location.values()
        )

        if total_assets != 20000:
            raise ValueError(
                f"Expected 20000 assets, found {total_assets}"
            )

        # 5. Distribute shipments proportionally across warehouses
        locations = list(assets_by_location.keys())

        exact_quotas = {
            location: (
                len(assets_by_location[location])
                * TOTAL_SHIPMENTS / total_assets
            )
            for location in locations
        }

        shipment_quotas = {
            location: int(exact_quotas[location])
            for location in locations
        }

        remaining = TOTAL_SHIPMENTS - sum(
            shipment_quotas.values()
        )

        remainder_order = sorted(
            locations,
            key=lambda location: (
                exact_quotas[location]
                - shipment_quotas[location]
            ),
            reverse=True
        )

        for location in remainder_order[:remaining]:
            shipment_quotas[location] += 1

        # 6. Generate shipment and assignment records
        shipment_records = []
        assignment_records = []

        shipment_number = 0

        for location_id in locations:

            location_assets = assets_by_location[location_id]

            rng.shuffle(location_assets)

            number_of_shipments = shipment_quotas[location_id]

            if number_of_shipments <= 0:
                raise ValueError(
                    f"No shipments allocated to {location_id}"
                )

            base_size, extra_assets = divmod(
                len(location_assets),
                number_of_shipments
            )

            asset_position = 0

            for group_number in range(number_of_shipments):

                shipment_number += 1

                shipment_id = (
                    f"SHP-2026-{shipment_number:06d}"
                )

                # Distribute assets evenly among shipments
                group_size = base_size

                if group_number < extra_assets:
                    group_size += 1

                assigned_assets = location_assets[
                    asset_position:asset_position + group_size
                ]

                asset_position += group_size

                if not assigned_assets:
                    raise ValueError(
                        f"Shipment {shipment_id} has no assets!"
                    )

                # Generate shipment information
                destination = rng.choice(customers)

                carrier = rng.choice(carriers)

                dispatch_date = (
                    datetime(2026, 1, 1)
                    + timedelta(days=rng.randint(0, 300))
                )

                expected_delivery = (
                    dispatch_date
                    + timedelta(days=rng.randint(1, 5))
                )

                shipment_records.append((
                    shipment_id,
                    location_id,
                    destination,
                    carrier,
                    dispatch_date.isoformat(timespec="seconds"),
                    expected_delivery.isoformat(timespec="seconds"),
                    "DISPATCHED"
                ))

                # Assign assets to shipment
                for asset_id in assigned_assets:

                    assignment_id = (
                        f"SA-{shipment_number:06d}-{asset_id}"
                    )

                    assignment_records.append((
                        assignment_id,
                        shipment_id,
                        asset_id,
                        dispatch_date.isoformat(timespec="seconds"),
                        None
                    ))

        # 7. Validate generated record counts
        if len(shipment_records) != TOTAL_SHIPMENTS:
            raise ValueError(
                "Shipment count does not match!"
            )

        if len(assignment_records) != total_assets:
            raise ValueError(
                "Asset assignment count does not match!"
            )

        # 8. Create DataFrames
        shipment_columns = [
            "shipment_id",
            "from_location_id",
            "to_location_id",
            "carrier_owner_id",
            "dispatch_date",
            "expected_delivery_date",
            "shipment_status"
        ]

        assignment_columns = [
            "shipment_asset_id",
            "shipment_id",
            "asset_id",
            "assigned_at",
            "removed_at"
        ]

        shipment_df = pd.DataFrame(
            shipment_records,
            columns=shipment_columns
        )

        assignment_df = pd.DataFrame(
            assignment_records,
            columns=assignment_columns
        )

        # 9. Export CSV files
        RAW_DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        shipment_df.to_csv(
            RAW_DATA_DIR / "shipments.csv",
            index=False
        )

        assignment_df.to_csv(
            RAW_DATA_DIR / "shipment_assets.csv",
            index=False
        )

        # 10. Remove previous generated shipment records
        cursor.execute("DELETE FROM ShipmentAsset")

        cursor.execute("DELETE FROM Shipment")

        # 11. Insert shipment records
        cursor.executemany("""
            INSERT INTO Shipment (
                shipment_id,
                from_location_id,
                to_location_id,
                carrier_owner_id,
                dispatch_date,
                expected_delivery_date,
                shipment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, shipment_records)

        # 12. Insert shipment-asset assignments
        cursor.executemany("""
            INSERT INTO ShipmentAsset (
                shipment_asset_id,
                shipment_id,
                asset_id,
                assigned_at,
                removed_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, assignment_records)

        connection.commit()

        # 13. Display results
        print("\nCorrected Shipment Generation Completed!")

        print("Total Shipments:", len(shipment_df))

        print(
            "Total Asset Assignments:",
            len(assignment_df)
        )

        print(
            "Unique Shipment IDs:",
            shipment_df["shipment_id"].nunique()
        )

        print(
            "Unique Assigned Assets:",
            assignment_df["asset_id"].nunique()
        )

        print("\nSample Shipments:")

        print(
            shipment_df.head(5).to_string(index=False)
        )

        print("\nCSV Files Generated:")

        print(RAW_DATA_DIR / "shipments.csv")

        print(RAW_DATA_DIR / "shipment_assets.csv")

    except Exception as error:

        connection.rollback()

        print("Error:", error)

        raise

    finally:

        connection.close()


if __name__ == "__main__":

    generate_shipments()

