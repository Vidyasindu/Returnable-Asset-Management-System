
import sqlite3
import random
import pandas as pd

from datetime import datetime, timedelta

from config import (
    DB_PATH,
    RAW_DATA_DIR,
    RANDOM_SEED,
    TOTAL_CUSTODY_EVENTS
)


def generate_custody_events():

    print("\nStarting Custody Event Generation...")

    rng = random.Random(RANDOM_SEED + 1)

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        cursor = connection.cursor()

        # 1. Fetch shipment and asset assignments
        cursor.execute("""
            SELECT
                sa.asset_id,
                sa.shipment_id,
                s.from_location_id,
                s.to_location_id,
                s.carrier_owner_id,
                s.dispatch_date,
                s.expected_delivery_date
            FROM ShipmentAsset sa
            JOIN Shipment s
                ON sa.shipment_id = s.shipment_id
            ORDER BY sa.asset_id
        """)

        shipment_assets = cursor.fetchall()

        if not shipment_assets:
            raise ValueError("No shipment assignments found!")

        # 2. Fetch customer locations
        cursor.execute("""
            SELECT location_id
            FROM Location
            WHERE location_type = 'CUSTOMER'
            ORDER BY location_id
        """)

        customer_locations = [
            row[0] for row in cursor.fetchall()
        ]

        # 3. Fetch customer owners
        cursor.execute("""
            SELECT owner_id
            FROM Owner
            WHERE owner_type = 'CUSTOMER'
            ORDER BY owner_id
        """)

        customer_owners = [
            row[0] for row in cursor.fetchall()
        ]

        if len(customer_locations) < 2:
            raise ValueError(
                "At least two customer locations are required!"
            )

        if not customer_owners:
            raise ValueError("No customer owners found!")

        if len(shipment_assets) != 20000:
            raise ValueError(
                f"Expected 20000 assignments, "
                f"found {len(shipment_assets)}"
            )

        # 4. Generate five custody events per asset
        event_records = []

        for (
            asset_id,
            shipment_id,
            from_location,
            to_location,
            carrier_id,
            dispatch_date,
            expected_delivery_date
        ) in shipment_assets:

            dispatch_time = datetime.fromisoformat(
                dispatch_date
            )

            delivery_time = datetime.fromisoformat(
                expected_delivery_date
            )

            # Choose a different customer location for transfer
            possible_destinations = [
                location
                for location in customer_locations
                if location != to_location
            ]

            transfer_location = rng.choice(
                possible_destinations
            )

            customer_actor = rng.choice(customer_owners)

            # Event 1: Asset dispatched from warehouse
            event_1_time = dispatch_time

            # Event 2: Asset received by customer
            event_2_time = delivery_time

            # Event 3: Asset transferred to another location
            event_3_time = (
                event_2_time
                + timedelta(days=rng.randint(1, 3))
            )

            # Event 4: Asset received at new location
            event_4_time = (
                event_3_time
                + timedelta(days=1)
            )

            # Event 5: Asset returned to original warehouse
            event_5_time = (
                event_4_time
                + timedelta(days=rng.randint(7, 30))
            )

            events = [
                (
                    "DISPATCH",
                    carrier_id,
                    from_location,
                    to_location,
                    event_1_time
                ),
                (
                    "RECEIVED",
                    customer_actor,
                    from_location,
                    to_location,
                    event_2_time
                ),
                (
                    "TRANSFER",
                    customer_actor,
                    to_location,
                    transfer_location,
                    event_3_time
                ),
                (
                    "RECEIVED",
                    customer_actor,
                    to_location,
                    transfer_location,
                    event_4_time
                ),
                (
                    "RETURN",
                    carrier_id,
                    transfer_location,
                    from_location,
                    event_5_time
                )
            ]

            for sequence, event in enumerate(events, start=1):

                (
                    event_type,
                    actor_id,
                    source_location,
                    destination_location,
                    event_time
                ) = event

                custody_event_id = (
                    f"CUST-{asset_id}-{sequence:06d}"
                )

                event_records.append((
                    custody_event_id,
                    asset_id,
                    shipment_id,
                    actor_id,
                    source_location,
                    destination_location,
                    event_type,
                    event_time.isoformat(timespec="seconds")
                ))

        # 5. Validate generated event count
        if len(event_records) != TOTAL_CUSTODY_EVENTS:
            raise ValueError(
                f"Expected {TOTAL_CUSTODY_EVENTS} events, "
                f"generated {len(event_records)}"
            )

        # 6. Create DataFrame
        columns = [
            "custody_event_id",
            "asset_id",
            "shipment_id",
            "actor_owner_id",
            "from_location_id",
            "to_location_id",
            "event_type",
            "event_timestamp"
        ]

        df = pd.DataFrame(
            event_records,
            columns=columns
        )

        # 7. Export CSV
        RAW_DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        csv_path = RAW_DATA_DIR / "custody_events.csv"

        df.to_csv(csv_path, index=False)

        # 8. Replace previously generated custody events
        cursor.execute("DELETE FROM CustodyEvent")

        # 9. Insert custody events
        cursor.executemany("""
            INSERT INTO CustodyEvent (
                custody_event_id,
                asset_id,
                shipment_id,
                actor_owner_id,
                from_location_id,
                to_location_id,
                event_type,
                event_timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, event_records)

        connection.commit()

        # 10. Display generation results
        print("\nCustody Event Generation Completed!")

        print("Total Custody Events:", len(df))

        print(
            "Unique Custody Event IDs:",
            df["custody_event_id"].nunique()
        )

        print(
            "Unique Assets:",
            df["asset_id"].nunique()
        )

        print("\nEvent Type Distribution:")

        print(df["event_type"].value_counts())

        print("\nSample Custody Events:")

        print(df.head(10).to_string(index=False))

        print("\nCSV Generated:")

        print(csv_path)

    except Exception as error:

        connection.rollback()

        print("Error:", error)

        raise

    finally:

        connection.close()


if __name__ == "__main__":

    generate_custody_events()

