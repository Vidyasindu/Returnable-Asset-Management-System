
import sqlite3


def get_anomaly_records(db_path):
    """
    Return the exact record identifiers for each detected anomaly.
    """

    checks = {
        "SIMULTANEOUS_LOCATIONS": """
            SELECT asset_id
            FROM CustodyEvent
            WHERE event_type = 'TRANSFER'
            GROUP BY asset_id, event_timestamp
            HAVING COUNT(DISTINCT to_location_id) > 1
        """,

        "RETURN_BEFORE_DISPATCH": """
            SELECT r.custody_event_id
            FROM CustodyEvent r
            WHERE r.event_type = 'RETURN'
            AND EXISTS (
                SELECT 1
                FROM CustodyEvent d
                WHERE d.asset_id = r.asset_id
                AND d.shipment_id = r.shipment_id
                AND d.event_type = 'DISPATCH'
                AND r.event_timestamp < d.event_timestamp
            )
        """,

        "DUPLICATE_REFUND": """
            SELECT reference_id
            FROM DepositLedger
            WHERE transaction_type = 'REFUND'
            GROUP BY asset_id, reference_id
            HAVING COUNT(*) > 1
        """,

        "REPAIR_INSPECTION_MISMATCH": """
            SELECT r.repair_id
            FROM Repair r
            JOIN Inspection i
                ON r.inspection_id = i.inspection_id
            WHERE r.asset_id != i.asset_id
        """,

        "MISSING_CUSTODY_ACTOR": """
            SELECT custody_event_id
            FROM CustodyEvent
            WHERE actor_owner_id IS NULL
        """,

        "SELF_TRANSFER": """
            SELECT custody_event_id
            FROM CustodyEvent
            WHERE event_type = 'TRANSFER'
            AND from_location_id = to_location_id
        """
    }

    results = {}

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()

        for name, query in checks.items():
            cursor.execute(query)
            results[name] = [row[0] for row in cursor.fetchall()]

    return results


def detect_anomalies(db_path):
    """
    Return anomaly counts for backward compatibility.
    """

    records = get_anomaly_records(db_path)

    return {
        name: len(record_ids)
        for name, record_ids in records.items()
    }


if __name__ == "__main__":
    database = "database/returnable_assets.db"

    records = get_anomaly_records(database)

    print("ANOMALY DETECTION RESULTS")
    print("-------------------------")

    for name, record_ids in records.items():
        print(f"{name}: {len(record_ids)}")
        print(f"Affected records: {record_ids}")
