
import sqlite3
import csv
import json
import random
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

# =====================================================
# 1. PROJECT CONFIGURATION
# =====================================================

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "database" / "returnable_assets.db"

SEED = 20261022
random.seed(SEED)

RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
GROUND = BASE / "data" / "ground_truth"
REPORTS = BASE / "reports"
DASHBOARD = BASE / "dashboard"

for folder in [PROCESSED, GROUND, REPORTS, DASHBOARD]:
    folder.mkdir(parents=True, exist_ok=True)

if not DB.exists():
    raise FileNotFoundError(f"Database not found: {DB}")

# Backup database before making changes
BACKUP = BASE / "database" / "returnable_assets_backup.db"

if not BACKUP.exists():
    shutil.copy2(DB, BACKUP)

connection = sqlite3.connect(DB)
connection.execute("PRAGMA foreign_keys = ON")
cursor = connection.cursor()

print("=" * 55)
print("RETURNABLE ASSET MANAGEMENT - PROJECT COMPLETION")
print("=" * 55)

# =====================================================
# 2. HELPER FUNCTIONS
# =====================================================

def next_number(table, column, prefix):
    cursor.execute(f"SELECT {column} FROM {table}")
    values = cursor.fetchall()

    numbers = []

    for row in values:
        try:
            numbers.append(int(row[0].split("-")[-1]))
        except (ValueError, AttributeError):
            pass

    return max(numbers, default=0) + 1


def next_event_number(asset_id):
    cursor.execute("""
        SELECT custody_event_id
        FROM CustodyEvent
        WHERE asset_id = ?
    """, (asset_id,))

    numbers = []

    for row in cursor.fetchall():
        try:
            numbers.append(int(row[0].split("-")[-1]))
        except (ValueError, AttributeError):
            pass

    return max(numbers, default=0) + 1


def add_event(asset_id, event_type, event_date,
              from_location, to_location,
              actor_id, shipment_id=None):

    event_id = (
        f"CUST-{asset_id}-"
        f"{next_event_number(asset_id):06d}"
    )

    cursor.execute("""
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
    """, (
        event_id,
        asset_id,
        shipment_id,
        actor_id,
        from_location,
        to_location,
        event_type,
        event_date
    ))

    return event_id


def record_anomaly(issue, entity_type, entity_id, description):
    cursor.execute("""
        INSERT INTO DataAnomaly (
            issue_type,
            entity_type,
            entity_id,
            ground_truth,
            description
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        issue,
        entity_type,
        str(entity_id),
        "ANOMALY",
        description
    ))


def export_csv(table):
    cursor.execute(f"SELECT * FROM {table}")

    columns = [item[0] for item in cursor.description]
    rows = cursor.fetchall()

    path = PROCESSED / f"{table.lower()}.csv"

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)

    return path


# =====================================================
# 3. START TRANSACTION AND CHECK PREVIOUS EXECUTION
# =====================================================

cursor.execute("""
    CREATE TABLE IF NOT EXISTS ProjectMetadata (
        metadata_key TEXT PRIMARY KEY,
        metadata_value TEXT
    )
""")

cursor.execute("""
    SELECT metadata_value
    FROM ProjectMetadata
    WHERE metadata_key = 'completion_v1'
""")

if cursor.fetchone():
    connection.close()
    print("\nProject completion script was already executed.")
    print("No duplicate records were created.")
    raise SystemExit

try:

    # =================================================
    # 4. GENERATE MISSING FINAL INSPECTIONS
    # =================================================

    cursor.execute("""
        SELECT MAX(CAST(SUBSTR(inspection_id, 10) AS INTEGER))
        FROM Inspection
    """)

    inspection_number = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT r.asset_id, r.repair_end_date
        FROM Repair r
        WHERE r.repair_status = 'COMPLETED'
        AND NOT EXISTS (
            SELECT 1
            FROM Inspection i
            WHERE i.asset_id = r.asset_id
            AND i.inspection_date >= r.repair_end_date
        )
    """)

    missing_inspections = cursor.fetchall()

    for asset_id, repair_date in missing_inspections:

        inspection_number += 1

        cursor.execute("""
            INSERT INTO Inspection (
                inspection_id,
                asset_id,
                inspection_date,
                asset_condition,
                inspection_result
            )
            VALUES (?, ?, ?, 'GOOD', 'PASS')
        """, (
            f"INS-2026-{inspection_number:06d}",
            asset_id,
            repair_date
        ))

    print("\nFinal inspections added:", len(missing_inspections))

    # =================================================
    # 5. CORRECT ASSET LIFECYCLE STATUSES
    # =================================================

    cursor.execute("""
        UPDATE ReusableAsset
        SET asset_status = 'AVAILABLE'
        WHERE asset_id IN (
            SELECT i.asset_id
            FROM Inspection i
            WHERE i.inspection_date = (
                SELECT MAX(i2.inspection_date)
                FROM Inspection i2
                WHERE i2.asset_id = i.asset_id
            )
            AND i.inspection_result = 'PASS'
        )
    """)

    cursor.execute("""
        UPDATE ReusableAsset
        SET asset_status = 'UNDER_REPAIR'
        WHERE asset_id IN (
            SELECT asset_id
            FROM Repair
            WHERE repair_status = 'IN_PROGRESS'
        )
    """)

    cursor.execute("""
        UPDATE ReusableAsset
        SET asset_status = 'DAMAGED'
        WHERE asset_id IN (
            SELECT asset_id
            FROM Repair
            WHERE repair_status = 'PENDING'
        )
    """)

    print("Asset lifecycle statuses corrected.")

    # =================================================
    # 6. FIND LOCATIONS AND ACTORS
    # =================================================

    cursor.execute("""
        SELECT location_id
        FROM Location
        WHERE location_type = 'CUSTOMER'
        ORDER BY location_id
    """)

    customer_locations = [r[0] for r in cursor.fetchall()]

    if not customer_locations:
        raise ValueError("No CUSTOMER location found.")

    customer_location = customer_locations[0]

    cursor.execute("""
        SELECT owner_id
        FROM Owner
        WHERE owner_type = 'LOGISTICS'
        LIMIT 1
    """)

    actor = cursor.fetchone()

    if not actor:
        raise ValueError("No LOGISTICS owner found.")

    actor_id = actor[0]

    # =================================================
    # 7. CREATE OVERDUE AND LOST RETURN SCENARIOS
    # =================================================

    cursor.execute("""
        SELECT MAX(event_timestamp)
        FROM CustodyEvent
    """)

    latest_event = datetime.fromisoformat(cursor.fetchone()[0])
    base_date = latest_event + timedelta(days=1)

    cursor.execute("""
        SELECT a.asset_id,
               a.current_location_id,
               a.asset_type_id,
               t.return_period_days
        FROM ReusableAsset a
        JOIN AssetType t
            ON a.asset_type_id = t.asset_type_id
        WHERE a.asset_status = 'AVAILABLE'
        ORDER BY a.asset_id
    """)

    candidates = cursor.fetchall()
    random.shuffle(candidates)

    if len(candidates) < 1000:
        raise ValueError("Not enough AVAILABLE assets for scenarios.")

    lost_assets = candidates[:200]
    overdue_assets = candidates[200:1000]

    rma_number = next_number(
        "ReturnAuthorization", "rma_id", "RMA-2026"
    )

    scenario_assets = []

    # Create 200 lost scenarios
    for index, item in enumerate(lost_assets):

        asset_id, old_location, asset_type, period = item

        event_date = base_date + timedelta(seconds=index)

        add_event(
            asset_id,
            "TRANSFER",
            event_date.isoformat(),
            old_location,
            customer_location,
            actor_id
        )

        new_rma = f"RMA-2026-{rma_number:06d}"
        rma_number += 1

        due_date = event_date + timedelta(days=period)

        cursor.execute("""
            INSERT INTO ReturnAuthorization (
                rma_id,
                asset_id,
                request_date,
                due_date,
                return_date,
                return_status
            )
            VALUES (?, ?, ?, ?, NULL, 'APPROVED')
        """, (
            new_rma,
            asset_id,
            event_date.isoformat(),
            due_date.isoformat()
        ))

        cursor.execute("""
            UPDATE ReusableAsset
            SET asset_status = 'LOST',
                current_location_id = ?
            WHERE asset_id = ?
        """, (customer_location, asset_id))

        scenario_assets.append(asset_id)

    # Create 800 overdue scenarios
    for index, item in enumerate(overdue_assets):

        asset_id, old_location, asset_type, period = item

        event_date = (
            base_date
            + timedelta(days=80, seconds=index)
        )

        add_event(
            asset_id,
            "TRANSFER",
            event_date.isoformat(),
            old_location,
            customer_location,
            actor_id
        )

        new_rma = f"RMA-2026-{rma_number:06d}"
        rma_number += 1

        due_date = event_date + timedelta(days=period)

        cursor.execute("""
            INSERT INTO ReturnAuthorization (
                rma_id,
                asset_id,
                request_date,
                due_date,
                return_date,
                return_status
            )
            VALUES (?, ?, ?, ?, NULL, 'APPROVED')
        """, (
            new_rma,
            asset_id,
            event_date.isoformat(),
            due_date.isoformat()
        ))

        cursor.execute("""
            UPDATE ReusableAsset
            SET asset_status = 'OVERDUE',
                current_location_id = ?
            WHERE asset_id = ?
        """, (customer_location, asset_id))

        scenario_assets.append(asset_id)

    scenario_as_of = base_date + timedelta(days=140)

    print("Lost scenarios created:", len(lost_assets))
    print("Overdue scenarios created:", len(overdue_assets))

    # =================================================
    # 8. GENERATE DEPOSIT LEDGER
    # =================================================

    transaction_number = next_number(
        "DepositLedger", "transaction_id", "DEP-2026"
    )

    cursor.execute("""
        SELECT r.rma_id,
               r.asset_id,
               r.request_date,
               r.return_date,
               r.return_status,
               a.deposit_amount
        FROM ReturnAuthorization r
        JOIN ReusableAsset a
            ON r.asset_id = a.asset_id
    """)

    rmas = cursor.fetchall()

    ledger_added = 0

    for rma in rmas:

        rma_id, asset_id, request_date, return_date, status, deposit = rma

        if deposit <= 0:
            continue

        cursor.execute("""
            SELECT COUNT(*)
            FROM DepositLedger
            WHERE reference_id = ?
            AND transaction_type = 'CHARGE'
        """, (rma_id,))

        if cursor.fetchone()[0]:
            continue

        cursor.execute("""
            INSERT INTO DepositLedger (
                transaction_id,
                asset_id,
                transaction_type,
                amount,
                transaction_date,
                reference_id
            )
            VALUES (?, ?, 'CHARGE', ?, ?, ?)
        """, (
            f"DEP-2026-{transaction_number:06d}",
            asset_id,
            deposit,
            request_date,
            rma_id
        ))

        transaction_number += 1
        ledger_added += 1

        if status != "RETURNED":
            continue

        cursor.execute("""
            SELECT inspection_result
            FROM Inspection
            WHERE asset_id = ?
            ORDER BY inspection_date DESC
            LIMIT 1
        """, (asset_id,))

        inspection = cursor.fetchone()

        cursor.execute("""
            SELECT repair_cost
            FROM Repair
            WHERE asset_id = ?
            ORDER BY repair_end_date DESC
            LIMIT 1
        """, (asset_id,))

        repair = cursor.fetchone()

        if inspection and inspection[0] == "PASS":
            deduction = 0
        else:
            repair_cost = repair[0] if repair else deposit
            deduction = min(deposit, repair_cost)

        refund = round(deposit - deduction, 2)
        deduction = round(deduction, 2)

        transaction_date = return_date or request_date

        if deduction > 0:

            cursor.execute("""
                INSERT INTO DepositLedger (
                    transaction_id,
                    asset_id,
                    transaction_type,
                    amount,
                    transaction_date,
                    reference_id
                )
                VALUES (?, ?, 'DEDUCTION', ?, ?, ?)
            """, (
                f"DEP-2026-{transaction_number:06d}",
                asset_id,
                deduction,
                transaction_date,
                rma_id
            ))

            transaction_number += 1

        if refund > 0:

            cursor.execute("""
                INSERT INTO DepositLedger (
                    transaction_id,
                    asset_id,
                    transaction_type,
                    amount,
                    transaction_date,
                    reference_id
                )
                VALUES (?, ?, 'REFUND', ?, ?, ?)
            """, (
                f"DEP-2026-{transaction_number:06d}",
                asset_id,
                refund,
                transaction_date,
                rma_id
            ))

            transaction_number += 1

    print("Deposit charges generated:", ledger_added)

    # =================================================
    # 9. CREATE ANOMALY GROUND TRUTH TABLE
    # =================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS DataAnomaly (
            anomaly_id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            ground_truth TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)

    # Select assets not used for overdue/lost scenarios
    cursor.execute("""
        SELECT asset_id, current_location_id
        FROM ReusableAsset
        WHERE asset_status = 'AVAILABLE'
        ORDER BY asset_id
        LIMIT 10
    """)

    anomaly_assets = cursor.fetchall()

    if len(anomaly_assets) < 4:
        raise ValueError("Not enough assets for anomaly injection.")

    # Anomaly 1: Same asset at two locations simultaneously
    asset_id, location_id = anomaly_assets[0]

    destinations = customer_locations[:2]

    if len(destinations) < 2:
        cursor.execute("""
            SELECT location_id
            FROM Location
            WHERE location_id != ?
            LIMIT 1
        """, (location_id,))
        extra = cursor.fetchone()

        if extra:
            destinations.append(extra[0])

    if len(destinations) < 2:
        raise ValueError("Two distinct locations are needed.")

    simultaneous_time = (
        scenario_as_of + timedelta(days=1)
    ).isoformat()

    event_one = add_event(
        asset_id, "TRANSFER", simultaneous_time,
        location_id, destinations[0], actor_id
    )

    event_two = add_event(
        asset_id, "TRANSFER", simultaneous_time,
        location_id, destinations[1], actor_id
    )

    record_anomaly(
        "SIMULTANEOUS_LOCATIONS",
        "ReusableAsset",
        asset_id,
        "Two custody transfers place the same asset at two locations at the same time."
    )

    # Anomaly 2: Return before dispatch
    asset_id = anomaly_assets[1][0]

    cursor.execute("""
        SELECT event_timestamp, shipment_id,
               from_location_id, to_location_id
        FROM CustodyEvent
        WHERE asset_id = ?
        AND event_type = 'DISPATCH'
        ORDER BY event_timestamp
        LIMIT 1
    """, (asset_id,))

    dispatch = cursor.fetchone()

    if dispatch:

        dispatch_date = datetime.fromisoformat(dispatch[0])
        invalid_date = (
            dispatch_date - timedelta(days=1)
        ).isoformat()

        event_id = add_event(
            asset_id,
            "RETURN",
            invalid_date,
            dispatch[3],
            dispatch[2],
            actor_id,
            dispatch[1]
        )

        record_anomaly(
            "RETURN_BEFORE_DISPATCH",
            "CustodyEvent",
            event_id,
            "Return event occurs before the corresponding dispatch."
        )

    # Anomaly 3: Duplicate refund
    cursor.execute("""
        SELECT asset_id, amount, transaction_date, reference_id
        FROM DepositLedger
        WHERE transaction_type = 'REFUND'
        LIMIT 1
    """)

    refund_record = cursor.fetchone()

    if refund_record:

        asset_id, amount, transaction_date, reference_id = refund_record

        cursor.execute("""
            INSERT INTO DepositLedger (
                transaction_id,
                asset_id,
                transaction_type,
                amount,
                transaction_date,
                reference_id
            )
            VALUES (?, ?, 'REFUND', ?, ?, ?)
        """, (
            f"DEP-2026-{transaction_number:06d}",
            asset_id,
            amount,
            transaction_date,
            reference_id
        ))

        transaction_number += 1

        record_anomaly(
            "DUPLICATE_REFUND",
            "DepositLedger",
            reference_id,
            "The same refund has been recorded twice."
        )

    # Anomaly 4: Repair linked to another asset's inspection
    asset_id = anomaly_assets[2][0]

    cursor.execute("""
        SELECT inspection_id, inspection_date
        FROM Inspection
        WHERE asset_id != ?
        AND inspection_id NOT IN (
            SELECT inspection_id FROM Repair
        )
        LIMIT 1
    """, (asset_id,))

    wrong_inspection = cursor.fetchone()

    if wrong_inspection:

        repair_number = next_number(
            "Repair", "repair_id", "REP-2026"
        )

        repair_start = (
            scenario_as_of + timedelta(days=2)
        )

        repair_end = repair_start + timedelta(days=2)

        repair_id = f"REP-2026-{repair_number:06d}"

        cursor.execute("""
            INSERT INTO Repair (
                repair_id,
                asset_id,
                inspection_id,
                repair_start_date,
                repair_end_date,
                repair_cost,
                repair_status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'COMPLETED')
        """, (
            repair_id,
            asset_id,
            wrong_inspection[0],
            repair_start.isoformat(),
            repair_end.isoformat(),
            250.00
        ))

        record_anomaly(
            "REPAIR_WITHOUT_VALID_ASSET_INSPECTION",
            "Repair",
            repair_id,
            "Repair references an inspection belonging to a different asset."
        )

    # Anomaly 5: Custody event without actor
    asset_id, location_id = anomaly_assets[3]

    missing_actor_event = add_event(
        asset_id,
        "TRANSFER",
        (scenario_as_of + timedelta(days=2)).isoformat(),
        location_id,
        location_id,
        None
    )

    record_anomaly(
        "MISSING_CUSTODY_ACTOR",
        "CustodyEvent",
        missing_actor_event,
        "Custody event has no responsible actor."
    )

    # =================================================
    # 10. SAVE EXECUTION MARKER
    # =================================================

    cursor.execute("""
        INSERT INTO ProjectMetadata (
            metadata_key,
            metadata_value
        )
        VALUES (?, ?)
    """, (
        "completion_v1",
        datetime.now().isoformat()
    ))

    cursor.execute("""
        INSERT OR REPLACE INTO ProjectMetadata (
            metadata_key,
            metadata_value
        )
        VALUES (?, ?)
    """, (
        "random_seed",
        str(SEED)
    ))

    cursor.execute("""
        INSERT OR REPLACE INTO ProjectMetadata (
            metadata_key,
            metadata_value
        )
        VALUES (?, ?)
    """, (
        "scenario_as_of_date",
        scenario_as_of.isoformat()
    ))

    connection.commit()

    print("\nBUSINESS DATA GENERATION COMPLETED")

except Exception as error:

    connection.rollback()
    connection.close()

    print("\nPROJECT ERROR:", error)
    print("Database transaction rolled back.")
    raise


# =====================================================
# 11. VALIDATION AND ANOMALY DETECTION
# =====================================================

connection = sqlite3.connect(DB)
cursor = connection.cursor()

validation = {}

tables = [
    "ReusableAsset",
    "Shipment",
    "ShipmentAsset",
    "CustodyEvent",
    "ReturnAuthorization",
    "Inspection",
    "Repair",
    "DepositLedger",
    "DataAnomaly"
]

for table in tables:

    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    validation[table] = cursor.fetchone()[0]

cursor.execute("PRAGMA foreign_key_check")
foreign_key_errors = len(cursor.fetchall())

cursor.execute("""
    SELECT asset_status, COUNT(*)
    FROM ReusableAsset
    GROUP BY asset_status
""")

asset_statuses = dict(cursor.fetchall())

cursor.execute("""
    SELECT shipment_status, COUNT(*)
    FROM Shipment
    GROUP BY shipment_status
""")

shipment_statuses = dict(cursor.fetchall())

cursor.execute("""
    SELECT return_status, COUNT(*)
    FROM ReturnAuthorization
    GROUP BY return_status
""")

return_statuses = dict(cursor.fetchall())

# Detect duplicate refunds
cursor.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT asset_id, reference_id
        FROM DepositLedger
        WHERE transaction_type = 'REFUND'
        GROUP BY asset_id, reference_id
        HAVING COUNT(*) > 1
    )
""")

duplicate_refunds = cursor.fetchone()[0]

# Detect missing custody actors
cursor.execute("""
    SELECT COUNT(*)
    FROM CustodyEvent
    WHERE actor_owner_id IS NULL
""")

missing_actors = cursor.fetchone()[0]

# Detect repair-inspection asset mismatches
cursor.execute("""
    SELECT COUNT(*)
    FROM Repair r
    JOIN Inspection i
        ON r.inspection_id = i.inspection_id
    WHERE r.asset_id != i.asset_id
""")

repair_mismatches = cursor.fetchone()[0]

# Detect returns before dispatch
cursor.execute("""
    SELECT COUNT(*)
    FROM CustodyEvent r
    WHERE r.event_type = 'RETURN'
    AND EXISTS (
        SELECT 1
        FROM CustodyEvent d
        WHERE d.asset_id = r.asset_id
        AND d.event_type = 'DISPATCH'
        AND r.event_timestamp < d.event_timestamp
    )
""")

returns_before_dispatch = cursor.fetchone()[0]

# Detect simultaneous locations
cursor.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT asset_id, event_timestamp
        FROM CustodyEvent
        WHERE event_type = 'TRANSFER'
        GROUP BY asset_id, event_timestamp
        HAVING COUNT(DISTINCT to_location_id) > 1
    )
""")

simultaneous_locations = cursor.fetchone()[0]

anomaly_detection = {
    "duplicate_refunds": duplicate_refunds,
    "missing_custody_actors": missing_actors,
    "repair_inspection_mismatches": repair_mismatches,
    "returns_before_dispatch": returns_before_dispatch,
    "simultaneous_locations": simultaneous_locations
}

# =====================================================
# 12. EXPORT CSV FILES
# =====================================================

export_tables = [
    "ReusableAsset",
    "Shipment",
    "CustodyEvent",
    "ReturnAuthorization",
    "Inspection",
    "Repair",
    "DepositLedger",
    "DataAnomaly"
]

for table in export_tables:
    export_csv(table)

# Export ground truth separately
export_csv("DataAnomaly")

shutil.copy2(
    PROCESSED / "dataanomaly.csv",
    GROUND / "ground_truth.csv"
)

# =====================================================
# 13. EXPORT JSON DATASET
# =====================================================

json_tables = [
    "ReusableAsset",
    "Shipment",
    "ShipmentAsset",
    "CustodyEvent",
    "ReturnAuthorization",
    "Inspection",
    "Repair",
    "DepositLedger",
    "DataAnomaly"
]

dataset = {}

for table in json_tables:

    cursor.execute(f"SELECT * FROM {table}")

    columns = [item[0] for item in cursor.description]

    dataset[table] = [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

with open(
    PROCESSED / "final_dataset.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(dataset, file, indent=2, default=str)

# =====================================================
# 14. EXPORT SQL SEED
# =====================================================

with open(
    BASE / "database" / "seed.sql",
    "w",
    encoding="utf-8"
) as file:

    for statement in connection.iterdump():
        file.write(statement + "\n")

# =====================================================
# 15. CREATE VALIDATION REPORT
# =====================================================

summary = {
    "random_seed": SEED,
    "scenario_as_of_date": scenario_as_of.isoformat()
        if "scenario_as_of" in locals()
        else None,
    "table_counts": validation,
    "asset_statuses": asset_statuses,
    "shipment_statuses": shipment_statuses,
    "return_statuses": return_statuses,
    "foreign_key_errors": foreign_key_errors,
    "anomaly_detection": anomaly_detection
}

with open(
    REPORTS / "validation_summary.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(summary, file, indent=4)

# =====================================================
# 16. CREATE SIMPLE HTML DASHBOARD
# =====================================================

html = f"""
<!DOCTYPE html>
<html>
<head>
<title>Returnable Asset Management Dashboard</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background: #f4f6f9;
    padding: 30px;
}}
h1 {{ color: #243b53; }}
.card {{
    background: white;
    padding: 20px;
    margin: 12px;
    display: inline-block;
    min-width: 180px;
    border-radius: 8px;
}}
.number {{
    font-size: 28px;
    font-weight: bold;
    color: #176b87;
}}
table {{
    border-collapse: collapse;
    background: white;
    margin-top: 20px;
    width: 70%;
}}
td, th {{
    padding: 12px;
    border: 1px solid #ddd;
    text-align: left;
}}
</style>
</head>
<body>

<h1>Returnable Asset Management Dashboard</h1>

<div class="card">
<h3>Total Assets</h3>
<div class="number">{validation['ReusableAsset']:,}</div>
</div>

<div class="card">
<h3>Total Shipments</h3>
<div class="number">{validation['Shipment']:,}</div>
</div>

<div class="card">
<h3>Custody Events</h3>
<div class="number">{validation['CustodyEvent']:,}</div>
</div>

<div class="card">
<h3>Deposit Transactions</h3>
<div class="number">{validation['DepositLedger']:,}</div>
</div>

<h2>Asset Status</h2>
<table>
<tr><th>Status</th><th>Count</th></tr>
{''.join(f'<tr><td>{k}</td><td>{v:,}</td></tr>' for k, v in asset_statuses.items())}
</table>

<h2>Shipment Status</h2>
<table>
<tr><th>Status</th><th>Count</th></tr>
{''.join(f'<tr><td>{k}</td><td>{v:,}</td></tr>' for k, v in shipment_statuses.items())}
</table>

<h2>Detected Anomalies</h2>
<table>
<tr><th>Anomaly</th><th>Count</th></tr>
{''.join(f'<tr><td>{k}</td><td>{v:,}</td></tr>' for k, v in anomaly_detection.items())}
</table>

<p>Random seed: {SEED}</p>
</body>
</html>
"""

with open(
    DASHBOARD / "index.html",
    "w",
    encoding="utf-8"
) as file:

    file.write(html)

# =====================================================
# 17. CREATE PROJECT DOCUMENTATION
# =====================================================

readme = f"""
# Returnable Asset Management System

## Project Overview

This project manages reusable assets, shipments, custody transfers,
return authorizations, inspections, repairs and deposits.

## Technology

- Python
- SQLite
- SQL
- CSV
- JSON
- HTML

## Dataset

- Assets: {validation['ReusableAsset']}
- Shipments: {validation['Shipment']}
- Custody Events: {validation['CustodyEvent']}
- Return Authorizations: {validation['ReturnAuthorization']}
- Inspections: {validation['Inspection']}
- Repairs: {validation['Repair']}
- Deposit Transactions: {validation['DepositLedger']}

## Business Rules

- Asset status is derived from inspection and repair records.
- Completed repairs receive a final GOOD/PASS inspection
  when no later inspection exists.
- Overdue and lost assets have open return authorizations.
- Deposit transactions record charges, deductions and refunds.
- Custody history is retained as event records.

## Anomaly Scenarios

- Simultaneous asset locations
- Return before dispatch
- Duplicate refund
- Repair linked to another asset's inspection
- Missing custody actor

## Reproducibility

Random seed: {SEED}

Scenario evaluation date: {summary['scenario_as_of_date']}

## Run

python src/complete_project.py

## Dashboard

Open dashboard/index.html in a browser.

## Validation

See reports/validation_summary.json.

## Ground Truth

See data/ground_truth/ground_truth.csv.
"""

with open(
    REPORTS / "FINAL_README.md",
    "w",
    encoding="utf-8"
) as file:

    file.write(readme)

# =====================================================
# 18. CREATE SOURCE MANIFEST
# =====================================================

manifest = {
    "seed": SEED,
    "database": DB.name,
    "table_counts": validation,
    "outputs": [
        "data/processed",
        "data/ground_truth/ground_truth.csv",
        "database/seed.sql",
        "reports/validation_summary.json",
        "reports/FINAL_README.md",
        "dashboard/index.html"
    ],
    "reproducibility_note": (
        "Fixed seed recorded. A second full database generation "
        "comparison has not yet been performed."
    )
}

with open(
    REPORTS / "source_manifest.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(manifest, file, indent=4)

connection.close()

# =====================================================
# 19. FINAL OUTPUT
# =====================================================

print("\n" + "=" * 55)
print("PROJECT COMPLETION SUMMARY")
print("=" * 55)

for table, count in validation.items():
    print(f"{table}: {count:,}")

print("\nASSET STATUSES:")
for status, count in asset_statuses.items():
    print(status, count)

print("\nANOMALY DETECTION:")
for issue, count in anomaly_detection.items():
    print(issue, count)

print("\nFOREIGN KEY ERRORS:", foreign_key_errors)

print("\nGENERATED OUTPUTS:")
print("CSV files:", PROCESSED)
print("JSON dataset:", PROCESSED / "final_dataset.json")
print("SQL seed:", BASE / "database" / "seed.sql")
print("Ground truth:", GROUND / "ground_truth.csv")
print("Validation:", REPORTS / "validation_summary.json")
print("Dashboard:", DASHBOARD / "index.html")
print("Documentation:", REPORTS / "FINAL_README.md")

print("\nPROJECT COMPLETION SCRIPT FINISHED.")
