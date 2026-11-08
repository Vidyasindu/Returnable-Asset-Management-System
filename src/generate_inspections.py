
import sqlite3
import random
import pandas as pd

from datetime import timedelta

from config import DB_PATH, RAW_DATA_DIR, RANDOM_SEED


def generate_inspections():

    print("\nStarting Inspection Generation...")

    rng = random.Random(RANDOM_SEED + 2)

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        cursor = connection.cursor()

        # 1. Fetch returned assets and their return dates
        cursor.execute("""
            SELECT
                asset_id,
                return_date
            FROM ReturnAuthorization
            WHERE return_status = 'RETURNED'
            ORDER BY asset_id
        """)

        assets = cursor.fetchall()

        if len(assets) != 20000:
            raise ValueError(
                f"Expected 20000 returned assets, found {len(assets)}"
            )

        # 2. Generate inspection records
        inspection_records = []

        for index, (asset_id, return_date) in enumerate(
            assets, start=1
        ):

            if not return_date:
                raise ValueError(
                    f"Missing return date for {asset_id}"
                )

            returned_on = pd.Timestamp(return_date)

            # Inspection occurs 0 to 3 days after return
            inspection_date = (
                returned_on
                + timedelta(days=rng.randint(0, 3))
            )

            # Generate asset condition
            probability = rng.random()

            if probability < 0.75:
                asset_condition = "GOOD"
                inspection_result = "PASS"

            elif probability < 0.95:
                asset_condition = "DAMAGED"
                inspection_result = "FAIL"

            else:
                asset_condition = "CRITICAL"
                inspection_result = "FAIL"

            inspection_id = f"INS-2026-{index:06d}"

            inspection_records.append((
                inspection_id,
                asset_id,
                inspection_date.isoformat(),
                asset_condition,
                inspection_result
            ))

        # 3. Validate generated count
        if len(inspection_records) != 20000:
            raise ValueError(
                "Inspection record count does not match!"
            )

        # 4. Create DataFrame
        columns = [
            "inspection_id",
            "asset_id",
            "inspection_date",
            "asset_condition",
            "inspection_result"
        ]

        df = pd.DataFrame(
            inspection_records,
            columns=columns
        )

        # 5. Export CSV
        RAW_DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        csv_path = RAW_DATA_DIR / "inspections.csv"

        df.to_csv(csv_path, index=False)

        # 6. Replace previous inspection records
        cursor.execute("DELETE FROM Inspection")

        # 7. Insert records into database
        cursor.executemany("""
            INSERT INTO Inspection (
                inspection_id,
                asset_id,
                inspection_date,
                asset_condition,
                inspection_result
            )
            VALUES (?, ?, ?, ?, ?)
        """, inspection_records)

        connection.commit()

        # 8. Display generation results
        print("\nInspection Generation Completed!")

        print("Total Inspections:", len(df))

        print(
            "Unique Inspection IDs:",
            df["inspection_id"].nunique()
        )

        print(
            "Unique Assets:",
            df["asset_id"].nunique()
        )

        print("\nAsset Condition Distribution:")

        print(df["asset_condition"].value_counts())

        print("\nInspection Result Distribution:")

        print(df["inspection_result"].value_counts())

        print("\nSample Inspection Records:")

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

    generate_inspections()
