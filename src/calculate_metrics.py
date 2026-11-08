
import sqlite3
import json
from pathlib import Path

from anomaly_detection import detect_anomalies


def calculate_metrics(db_path):

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    metrics = {}

    # Asset metrics
    cursor.execute("""
        SELECT asset_status, COUNT(*)
        FROM ReusableAsset
        GROUP BY asset_status
    """)
    metrics["asset_status"] = dict(cursor.fetchall())

    # Shipment metrics
    cursor.execute("""
        SELECT shipment_status, COUNT(*)
        FROM Shipment
        GROUP BY shipment_status
    """)
    metrics["shipment_status"] = dict(cursor.fetchall())

    # Return metrics
    cursor.execute("""
        SELECT return_status, COUNT(*)
        FROM ReturnAuthorization
        GROUP BY return_status
    """)
    metrics["return_status"] = dict(cursor.fetchall())

    # Deposit metrics
    cursor.execute("""
        SELECT transaction_type,
               COUNT(*),
               ROUND(SUM(amount), 2)
        FROM DepositLedger
        GROUP BY transaction_type
    """)

    metrics["deposit_summary"] = {
        row[0]: {
            "transactions": row[1],
            "total_amount": row[2]
        }
        for row in cursor.fetchall()
    }

    # Total records
    tables = [
        "ReusableAsset",
        "Shipment",
        "CustodyEvent",
        "ReturnAuthorization",
        "Inspection",
        "Repair",
        "DepositLedger"
    ]

    metrics["record_counts"] = {}

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        metrics["record_counts"][table] = cursor.fetchone()[0]

    # Foreign key validation
    cursor.execute("PRAGMA foreign_key_check")
    metrics["foreign_key_errors"] = len(cursor.fetchall())

    # Anomaly detection
    connection.close()

    metrics["detected_anomalies"] = detect_anomalies(db_path)

    # Ground truth comparison
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT issue_type
        FROM DataAnomaly
        WHERE ground_truth = 'ANOMALY'
    """)

    ground_truth = set(row[0] for row in cursor.fetchall())

    detected_mapping = {
        "SIMULTANEOUS_LOCATIONS": "SIMULTANEOUS_LOCATIONS",
        "RETURN_BEFORE_DISPATCH": "RETURN_BEFORE_DISPATCH",
        "DUPLICATE_REFUND": "DUPLICATE_REFUND",
        "REPAIR_WITHOUT_VALID_ASSET_INSPECTION": "REPAIR_INSPECTION_MISMATCH",
        "MISSING_CUSTODY_ACTOR": "MISSING_CUSTODY_ACTOR"
    }

    detected = metrics["detected_anomalies"]

    true_positive = sum(
        1 for truth, detection in detected_mapping.items()
        if truth in ground_truth and detected.get(detection, 0) > 0
    )

    false_negative = len(ground_truth) - true_positive

    false_positive = sum(
        1 for truth, detection in detected_mapping.items()
        if truth not in ground_truth and detected.get(detection, 0) > 0
    )

    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive else 0
    )

    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative else 0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    metrics["evaluation"] = {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4)
    }

    connection.close()

    return metrics


if __name__ == "__main__":

    database = "database/returnable_assets.db"

    results = calculate_metrics(database)

    print("\nPROJECT PERFORMANCE METRICS")
    print("=" * 35)

    print(json.dumps(results, indent=4))

    output = Path("reports/project_metrics.json")
    output.parent.mkdir(exist_ok=True)

    with open(output, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    print("\nMetrics saved to:", output)
