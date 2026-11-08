
import sqlite3
import random
import pandas as pd

from datetime import timedelta

from config import DB_PATH, RAW_DATA_DIR, RANDOM_SEED


def generate_repairs():

    print("\nStarting Repair Generation...")

    rng = random.Random(RANDOM_SEED + 3)

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        cursor = connection.cursor()

        # 1. Fetch assets that failed inspection
        cursor.execute("""
            SELECT
                inspection_id,
                asset_id,
                inspection_date,
                asset_condition
            FROM Inspection
            WHERE inspection_result = 'FAIL'
            ORDER BY asset_id
        """)

        failed_inspections = cursor.fetchall()

        if not failed_inspections:
            raise ValueError("No failed inspections found!")

        # 2. Generate repair records
        repair_records = []

        for index, row in enumerate(
            failed_inspections, start=1
        ):

            (
                inspection_id,
                asset_id,
                inspection_date,
                asset_condition
            ) = row

            inspection_datetime = pd.Timestamp(
                inspection_date
            )

            # Repair starts 1 to 5 days after inspection
            repair_start = (
                inspection_datetime
                + timedelta(days=rng.randint(1, 5))
            )

            # Generate repair cost based on asset condition
            if asset_condition == "DAMAGED":
                repair_cost = round(
                    rng.uniform(200, 1000), 2
                )

            elif asset_condition == "CRITICAL":
                repair_cost = round(
                    rng.uniform(1000, 3000), 2
                )

            else:
                raise ValueError(
                    f"Unexpected failed condition: {asset_condition}"
                )

            # Generate repair status
            probability = rng.random()

            if probability < 0.70:

                repair_status = "COMPLETED"

                repair_end = (
                    repair_start
                    + timedelta(days=rng.randint(1, 14))
                )

                repair_end_date = repair_end.isoformat()

            elif probability < 0.90:

                repair_status = "IN_PROGRESS"
                repair_end_date = None

            else:

                repair_status = "PENDING"
                repair_end_date = None

            repair_id = f"REP-2026-{index:06d}"

            repair_records.append((
                repair_id,
                asset_id,
                inspection_id,
                repair_start.isoformat(),
                repair_end_date,
                repair_cost,
                repair_status
            ))

        # 3. Validate generated count
        if len(repair_records) != len(failed_inspections):
            raise ValueError(
                "Repair record count does not match!"
            )

        # 4. Create DataFrame
        columns = [
            "repair_id",
            "asset_id",
            "inspection_id",
            "repair_start_date",
            "repair_end_date",
            "repair_cost",
            "repair_status"
        ]

        df = pd.DataFrame(
            repair_records,
            columns=columns
        )

        # 5. Export CSV
        RAW_DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        csv_path = RAW_DATA_DIR / "repairs.csv"

        df.to_csv(csv_path, index=False)

        # 6. Replace previous repair records
        cursor.execute("DELETE FROM Repair")

        # 7. Insert repair records
        cursor.executemany("""
            INSERT INTO Repair (
                repair_id,
                asset_id,
                inspection_id,
                repair_start_date,
                repair_end_date,
                repair_cost,
                repair_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, repair_records)

        connection.commit()

        # 8. Display results
        print("\nRepair Generation Completed!")

        print("Total Repair Records:", len(df))

        print(
            "Unique Repair IDs:",
            df["repair_id"].nunique()
        )

        print(
            "Unique Assets:",
            df["asset_id"].nunique()
        )

        print("\nRepair Status Distribution:")

        print(df["repair_status"].value_counts())

        print("\nRepair Cost Summary:")

        print(df["repair_cost"].describe())

        print("\nSample Repair Records:")

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

    generate_repairs()
