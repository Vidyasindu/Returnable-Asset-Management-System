
import sqlite3
import pandas as pd

from datetime import timedelta

from config import DB_PATH, RAW_DATA_DIR


def generate_return_authorizations():

    print("\nStarting Return Authorization Generation...")

    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        cursor = connection.cursor()

        # 1. Fetch asset, return period, and custody dates
        cursor.execute("""
            SELECT
                a.asset_id,
                at.return_period_days,
                MAX(
                    CASE
                        WHEN ce.event_type = 'RECEIVED'
                        THEN ce.event_timestamp
                    END
                ) AS last_received_date,
                MAX(
                    CASE
                        WHEN ce.event_type = 'RETURN'
                        THEN ce.event_timestamp
                    END
                ) AS actual_return_date
            FROM ReusableAsset a
            JOIN AssetType at
                ON a.asset_type_id = at.asset_type_id
            JOIN CustodyEvent ce
                ON a.asset_id = ce.asset_id
            GROUP BY
                a.asset_id,
                at.return_period_days
            ORDER BY a.asset_id
        """)

        assets = cursor.fetchall()

        if len(assets) != 20000:
            raise ValueError(
                f"Expected 20000 assets, found {len(assets)}"
            )

        # 2. Generate RMA records
        rma_records = []

        for index, row in enumerate(assets, start=1):

            (
                asset_id,
                return_period_days,
                last_received_date,
                actual_return_date
            ) = row

            if not last_received_date or not actual_return_date:
                raise ValueError(
                    f"Missing custody dates for {asset_id}"
                )

            request_date = pd.Timestamp(
                last_received_date
            )

            return_date = pd.Timestamp(
                actual_return_date
            )

            if return_date < request_date:
                raise ValueError(
                    f"Return date before request date: {asset_id}"
                )

            # Calculate expected return deadline
            due_date = (
                request_date
                + timedelta(days=return_period_days)
            )

            rma_id = f"RMA-2026-{index:06d}"

            return_status = "RETURNED"

            rma_records.append((
                rma_id,
                asset_id,
                request_date.isoformat(),
                due_date.isoformat(),
                return_date.isoformat(),
                return_status
            ))

        # 3. Create DataFrame
        columns = [
            "rma_id",
            "asset_id",
            "request_date",
            "due_date",
            "return_date",
            "return_status"
        ]

        df = pd.DataFrame(
            rma_records,
            columns=columns
        )

        # 4. Export CSV
        RAW_DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        csv_path = (
            RAW_DATA_DIR / "return_authorizations.csv"
        )

        df.to_csv(csv_path, index=False)

        # 5. Replace existing RMA records
        cursor.execute(
            "DELETE FROM ReturnAuthorization"
        )

        # 6. Insert records into database
        cursor.executemany("""
            INSERT INTO ReturnAuthorization (
                rma_id,
                asset_id,
                request_date,
                due_date,
                return_date,
                return_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, rma_records)

        connection.commit()

        # 7. Display results
        print("\nReturn Authorization Generation Completed!")

        print("Total RMA Records:", len(df))

        print(
            "Unique RMA IDs:",
            df["rma_id"].nunique()
        )

        print(
            "Unique Assets:",
            df["asset_id"].nunique()
        )

        print("\nReturn Status Distribution:")

        print(df["return_status"].value_counts())

        print("\nSample RMA Records:")

        print(df.head(5).to_string(index=False))

        print("\nCSV Generated:")

        print(csv_path)

    except Exception as error:

        connection.rollback()

        print("Error:", error)

        raise

    finally:

        connection.close()


if __name__ == "__main__":

    generate_return_authorizations()
