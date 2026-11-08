
import sqlite3
import pandas as pd
from pathlib import Path


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = PROJECT_ROOT / "database" / "returnable_assets.db"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

EXPECTED_ASSETS = 20000
EXPECTED_SHIPMENTS = 10000
EXPECTED_CUSTODY_EVENTS = 101004
EXPECTED_RMAS = 21000
EXPECTED_INSPECTIONS = 23483
EXPECTED_REPAIRS = 4953

EXPECTED_EVENT_DISTRIBUTION = {
    5: 18997,
    6: 1002,
    7: 1
}

EXPECTED_ADDITIONAL_RMAS = {
    ("LOST", "APPROVED"): 200,
    ("OVERDUE", "APPROVED"): 800
}

EXPECTED_ANOMALIES = {
    "SIMULTANEOUS_LOCATIONS",
    "RETURN_BEFORE_DISPATCH",
    "DUPLICATE_REFUND",
    "REPAIR_WITHOUT_VALID_ASSET_INSPECTION",
    "MISSING_CUSTODY_ACTOR"
}


# ============================================================
# COMMON HELPER FUNCTIONS
# ============================================================

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def read_raw_csv(filename):
    path = RAW_DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Raw CSV file not found: {path}"
        )

    return pd.read_csv(path)


def get_csv_ids(df, column):
    if column not in df.columns:
        raise ValueError(
            f"Column '{column}' not found in raw CSV"
        )

    return set(
        df[column].dropna().astype(str)
    )


def get_database_ids(cursor, table, column):
    cursor.execute(
        f"SELECT {column} FROM {table}"
    )
    return {str(row[0]) for row in cursor.fetchall()}


def foreign_key_error_count(cursor):
    cursor.execute("PRAGMA foreign_key_check")
    return len(cursor.fetchall())


def print_result(name, passed):
    status = "PASS" if passed else "FAIL"
    print(f"{name}: {status}")


# ============================================================
# 1. ASSET DATA VALIDATION
# ============================================================

def validate_reusable_assets():

    print("\n===== ASSET DATA VALIDATION =====")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM ReusableAsset
        """)
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) - COUNT(DISTINCT asset_id)
            FROM ReusableAsset
        """)
        duplicates = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ReusableAsset
            WHERE asset_id IS NULL
               OR asset_type_id IS NULL
               OR owner_id IS NULL
               OR asset_status IS NULL
               OR purchase_date IS NULL
               OR deposit_amount IS NULL
        """)
        missing = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ReusableAsset
            WHERE asset_id NOT GLOB 'ASSET-[0-9]*'
        """)
        invalid_ids = cursor.fetchone()[0]

        fk_errors = foreign_key_error_count(cursor)

        cursor.execute("""
            SELECT COUNT(*)
            FROM ReusableAsset
            WHERE deposit_amount < 0
        """)
        invalid_deposits = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ReusableAsset
            WHERE asset_status NOT IN (
                'AVAILABLE',
                'DAMAGED',
                'LOST',
                'OVERDUE',
                'UNDER_REPAIR'
            )
        """)
        invalid_statuses = cursor.fetchone()[0]

        raw = read_raw_csv("reusable_assets.csv")
        raw_count = len(raw)

        print("1. Total Records:", total)
        print("2. Duplicate Asset IDs:", duplicates)
        print("3. Missing Values:", missing)
        print("4. Invalid Asset IDs:", invalid_ids)
        print("5. Foreign Key Errors:", fk_errors)
        print("6. Invalid Deposits:", invalid_deposits)
        print("7. Invalid Statuses:", invalid_statuses)
        print("8. CSV Records:", raw_count)
        print("9. Database Records:", total)
        print(
            "10. CSV and Database Counts Match:",
            raw_count == total
        )

        passed = (
            total == EXPECTED_ASSETS
            and duplicates == 0
            and missing == 0
            and invalid_ids == 0
            and fk_errors == 0
            and invalid_deposits == 0
            and invalid_statuses == 0
            and raw_count == total
        )

        if passed:
            print("\nSUCCESS: All Asset Validations Passed!")
        else:
            print("\nWARNING: Asset Validation Requires Investigation!")

    finally:
        connection.close()


# ============================================================
# 2. SHIPMENT DATA VALIDATION
# ============================================================

def validate_shipments():

    print("\n===== SHIPMENT DATA VALIDATION =====")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM Shipment
        """)
        total_shipments = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM ShipmentAsset
        """)
        assignments = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT asset_id
                FROM ShipmentAsset
                GROUP BY asset_id
                HAVING COUNT(*) > 1
            )
        """)
        duplicate_assignments = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM Shipment s
            WHERE NOT EXISTS (
                SELECT 1
                FROM ShipmentAsset sa
                WHERE sa.shipment_id = s.shipment_id
            )
        """)
        empty_shipments = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ShipmentAsset sa
            JOIN Shipment s
              ON sa.shipment_id = s.shipment_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM CustodyEvent ce
                WHERE ce.asset_id = sa.asset_id
                  AND ce.shipment_id = sa.shipment_id
                  AND ce.event_type = 'DISPATCH'
                  AND ce.from_location_id = s.from_location_id
            )
        """)
        origin_mismatches = cursor.fetchone()[0]

        fk_errors = foreign_key_error_count(cursor)

        print("1. Total Shipments:", total_shipments)
        print("2. Total Asset Assignments:", assignments)
        print("3. Assets Assigned More Than Once:",
              duplicate_assignments)
        print("4. Shipments Without Assets:", empty_shipments)
        print("5. Asset and Shipment Origin Mismatches:",
              origin_mismatches)
        print("6. Foreign Key Errors:", fk_errors)

        passed = (
            total_shipments == EXPECTED_SHIPMENTS
            and assignments == 20000
            and duplicate_assignments == 0
            and empty_shipments == 0
            and origin_mismatches == 0
            and fk_errors == 0
        )

        if passed:
            print("\nSUCCESS: All Shipment Validations Passed!")
        else:
            print("\nWARNING: Shipment Validation Requires Investigation!")

    finally:
        connection.close()


# ============================================================
# 3. CUSTODY EVENT VALIDATION
# ============================================================

def validate_custody_events():

    print("\n===== CUSTODY EVENT VALIDATION =====")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM CustodyEvent
        """)
        total_events = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT custody_event_id)
            FROM CustodyEvent
        """)
        unique_ids = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT asset_id)
            FROM CustodyEvent
        """)
        unique_assets = cursor.fetchone()[0]

        cursor.execute("""
            SELECT event_count, COUNT(*)
            FROM (
                SELECT asset_id, COUNT(*) AS event_count
                FROM CustodyEvent
                GROUP BY asset_id
            )
            GROUP BY event_count
        """)
        distribution = dict(cursor.fetchall())

        cursor.execute("""
            SELECT custody_event_id
            FROM CustodyEvent
            WHERE actor_owner_id IS NULL
        """)
        missing_actor_ids = {
            row[0] for row in cursor.fetchall()
        }

        cursor.execute("""
            SELECT entity_id
            FROM DataAnomaly
            WHERE issue_type = 'MISSING_CUSTODY_ACTOR'
              AND entity_type = 'CustodyEvent'
              AND ground_truth = 'ANOMALY'
        """)
        expected_actor_ids = {
            row[0] for row in cursor.fetchall()
        }

        actor_match = (
            missing_actor_ids == expected_actor_ids
        )

        cursor.execute("""
            SELECT COUNT(*)
            FROM CustodyEvent
            WHERE event_type NOT IN (
                'DISPATCH',
                'RECEIVED',
                'TRANSFER',
                'RETURN'
            )
        """)
        invalid_types = cursor.fetchone()[0]

        fk_errors = foreign_key_error_count(cursor)

        cursor.execute("""
            SELECT COUNT(*)
            FROM CustodyEvent
            WHERE from_location_id IS NULL
               OR to_location_id IS NULL
        """)
        missing_locations = cursor.fetchone()[0]

        raw = read_raw_csv("custody_events.csv")
        raw_count = len(raw)

        generated_events = total_events - raw_count

        expected_generated_events = 1004

        print("1. Total Custody Events:", total_events)
        print("2. Unique Event IDs:", unique_ids)
        print("3. Unique Assets:", unique_assets)
        print("4. Events Per Asset:", distribution)
        print("   Expected Distribution:",
              EXPECTED_EVENT_DISTRIBUTION)
        print("5. Missing Actors:", len(missing_actor_ids))
        print("   Expected Injected Actor Anomalies:",
              len(expected_actor_ids))
        print("   Matches Ground Truth:", actor_match)
        print("6. Invalid Event Types:", invalid_types)
        print("7. Foreign Key Errors:", fk_errors)
        print("8. Events With Missing Locations:",
              missing_locations)
        print("9. Original CSV Records:", raw_count)
        print("   Additional Generated Events:",
              generated_events)
        print("10. Expected Database Records:",
              raw_count + expected_generated_events)

        generated_count_valid = (
            generated_events == expected_generated_events
        )

        passed = (
            total_events == EXPECTED_CUSTODY_EVENTS
            and unique_ids == total_events
            and unique_assets == EXPECTED_ASSETS
            and distribution == EXPECTED_EVENT_DISTRIBUTION
            and actor_match
            and invalid_types == 0
            and fk_errors == 0
            and missing_locations == 0
            and generated_count_valid
        )

        if passed:
            print("\nSUCCESS: Custody Structure Validated!")
            print(
                "Note: Intentional missing-actor anomaly "
                "matches ground truth."
            )
        else:
            print("\nWARNING: Custody Validation Requires Investigation!")

    finally:
        connection.close()


# ============================================================
# 4. RETURN AUTHORIZATION VALIDATION
# ============================================================

def validate_return_authorizations():

    print("\n===== RETURN AUTHORIZATION VALIDATION =====")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM ReturnAuthorization
        """)
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT rma_id)
            FROM ReturnAuthorization
        """)
        unique_rmas = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT asset_id)
            FROM ReturnAuthorization
        """)
        unique_assets = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ReturnAuthorization
            WHERE due_date < request_date
        """)
        invalid_due_dates = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ReturnAuthorization
            WHERE return_date IS NOT NULL
              AND return_date < request_date
        """)
        invalid_return_dates = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ReturnAuthorization
            WHERE return_status NOT IN (
                'PENDING',
                'APPROVED',
                'RETURNED',
                'CANCELLED'
            )
        """)
        invalid_statuses = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM ReturnAuthorization
            WHERE (return_status = 'RETURNED'
                   AND return_date IS NULL)
               OR (return_status = 'APPROVED'
                   AND return_date IS NOT NULL)
        """)
        status_date_mismatches = cursor.fetchone()[0]

        fk_errors = foreign_key_error_count(cursor)

        raw = read_raw_csv("return_authorizations.csv")
        raw_ids = get_csv_ids(raw, "rma_id")
        db_ids = get_database_ids(
            cursor, "ReturnAuthorization", "rma_id"
        )

        missing_original_ids = raw_ids - db_ids
        additional_ids = db_ids - raw_ids

        cursor.execute("""
            SELECT a.asset_status, r.return_status, COUNT(*)
            FROM ReturnAuthorization r
            JOIN ReusableAsset a
              ON r.asset_id = a.asset_id
            WHERE r.rma_id IN (
                SELECT rma_id
                FROM ReturnAuthorization
            )
            GROUP BY a.asset_status, r.return_status
        """)

        # Verify only the additional records against their
        # expected generated scenarios.
        additional_counts = {}

        cursor.execute("""
            SELECT r.rma_id, r.return_status, r.return_date,
                   a.asset_status
            FROM ReturnAuthorization r
            JOIN ReusableAsset a
              ON r.asset_id = a.asset_id
        """)

        for rma_id, status, return_date, asset_status in cursor.fetchall():
            if rma_id in additional_ids:
                key = (asset_status, status)
                additional_counts[key] = (
                    additional_counts.get(key, 0) + 1
                )

                if status != "APPROVED" or return_date is not None:
                    additional_counts["INVALID"] = 1

        generated_valid = (
            additional_counts == EXPECTED_ADDITIONAL_RMAS
        )

        print("1. Total RMA Records:", total)
        print("2. Unique RMA IDs:", unique_rmas)
        print("3. Unique Assets:", unique_assets)
        print("4. Invalid Due Dates:", invalid_due_dates)
        print("5. Invalid Return Dates:", invalid_return_dates)
        print("6. Invalid Return Statuses:", invalid_statuses)
        print("7. Status and Return-Date Mismatches:",
              status_date_mismatches)
        print("8. Foreign Key Errors:", fk_errors)
        print("9. Original CSV Records:", len(raw))
        print("   Original IDs Missing From Database:",
              len(missing_original_ids))
        print("   Additional Generated Records:",
              len(additional_ids))
        print("10. Additional Records by Asset Status:",
              additional_counts)
        print("    Generated Scenarios Valid:", generated_valid)

        passed = (
            total == EXPECTED_RMAS
            and unique_rmas == total
            and unique_assets == EXPECTED_ASSETS
            and invalid_due_dates == 0
            and invalid_return_dates == 0
            and invalid_statuses == 0
            and status_date_mismatches == 0
            and fk_errors == 0
            and len(missing_original_ids) == 0
            and len(additional_ids) == 1000
            and generated_valid
        )

        if passed:
            print("\nSUCCESS: All Return Authorization Validations Passed!")
        else:
            print("\nWARNING: Return Authorization Validation Requires Investigation!")

    finally:
        connection.close()


# ============================================================
# 5. INSPECTION DATA VALIDATION
# ============================================================

def validate_inspections():

    print("\n===== INSPECTION DATA VALIDATION =====")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM Inspection
        """)
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT inspection_id)
            FROM Inspection
        """)
        unique_ids = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT asset_id)
            FROM Inspection
        """)
        unique_assets = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM Inspection
            WHERE asset_condition IS NULL
               OR TRIM(asset_condition) = ''
        """)
        invalid_conditions = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM Inspection
            WHERE inspection_result IS NULL
               OR TRIM(inspection_result) = ''
        """)
        invalid_results = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM Inspection
            WHERE inspection_date IS NULL
               OR TRIM(inspection_date) = ''
        """)
        invalid_dates = cursor.fetchone()[0]

        # Check inspection dates against returned RMAs.
        # Only compare with an RMA for the same asset.
        cursor.execute("""
            SELECT COUNT(*)
            FROM Inspection i
            WHERE EXISTS (
                SELECT 1
                FROM ReturnAuthorization r
                WHERE r.asset_id = i.asset_id
                  AND r.return_status = 'RETURNED'
                  AND r.return_date IS NOT NULL
                  AND i.inspection_date < r.return_date
            )
        """)
        inspections_before_return = cursor.fetchone()[0]

        fk_errors = foreign_key_error_count(cursor)

        raw = read_raw_csv("inspections.csv")
        raw_ids = get_csv_ids(raw, "inspection_id")
        db_ids = get_database_ids(
            cursor, "Inspection", "inspection_id"
        )

        missing_original_ids = raw_ids - db_ids
        additional_ids = db_ids - raw_ids

        additional_valid = (
            len(additional_ids) == 3483
            and len(missing_original_ids) == 0
        )

        print("1. Total Inspections:", total)
        print("2. Unique Inspection IDs:", unique_ids)
        print("3. Unique Inspected Assets:", unique_assets)
        print("4. Invalid Conditions:", invalid_conditions)
        print("5. Invalid Inspection Results:", invalid_results)
        print("6. Invalid Inspection Dates:", invalid_dates)
        print("7. Inspections Before Return:",
              inspections_before_return)
        print("8. Foreign Key Errors:", fk_errors)
        print("9. Original CSV Records:", len(raw))
        print("   Original IDs Missing From Database:",
              len(missing_original_ids))
        print("   Additional Generated Inspections:",
              len(additional_ids))
        print("   Generated Inspection Count Valid:",
              additional_valid)

        passed = (
            total == EXPECTED_INSPECTIONS
            and unique_ids == total
            and unique_assets == EXPECTED_ASSETS
            and invalid_conditions == 0
            and invalid_results == 0
            and invalid_dates == 0
            and inspections_before_return == 0
            and fk_errors == 0
            and additional_valid
        )

        if passed:
            print("\nSUCCESS: Inspection Data Structure Validated!")
        else:
            print("\nWARNING: Inspection Validation Requires Investigation!")

    finally:
        connection.close()


# ============================================================
# 6. REPAIR DATA VALIDATION
# ============================================================

def validate_repairs():

    print("\n===== REPAIR DATA VALIDATION =====")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM Repair
        """)
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT repair_id)
            FROM Repair
        """)
        unique_ids = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT asset_id)
            FROM Repair
        """)
        unique_assets = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM Repair
            WHERE repair_cost < 0
        """)
        invalid_costs = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM Repair
            WHERE repair_status IS NULL
               OR TRIM(repair_status) = ''
        """)
        invalid_statuses = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM Repair
            WHERE repair_status = 'COMPLETED'
              AND repair_end_date IS NULL
        """)
        completed_without_end_date = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM Repair
            WHERE repair_status != 'COMPLETED'
              AND repair_end_date IS NOT NULL
        """)
        unfinished_with_end_date = cursor.fetchone()[0]

        # Find repairs whose linked inspection did not fail.
        cursor.execute("""
            SELECT r.repair_id
            FROM Repair r
            JOIN Inspection i
              ON r.inspection_id = i.inspection_id
            WHERE i.inspection_result != 'FAIL'
        """)
        repairs_without_failed_inspection = {
            row[0] for row in cursor.fetchall()
        }

        # Find repairs linked to inspections belonging to
        # a different asset.
        cursor.execute("""
            SELECT r.repair_id
            FROM Repair r
            JOIN Inspection i
              ON r.inspection_id = i.inspection_id
            WHERE r.asset_id != i.asset_id
        """)
        repair_asset_mismatches = {
            row[0] for row in cursor.fetchall()
        }

        cursor.execute("""
            SELECT COUNT(*)
            FROM Repair r
            JOIN Inspection i
              ON r.inspection_id = i.inspection_id
            WHERE r.repair_start_date < i.inspection_date
        """)
        repairs_before_inspection = cursor.fetchone()[0]

        fk_errors = foreign_key_error_count(cursor)

        raw = read_raw_csv("repairs.csv")
        raw_ids = get_csv_ids(raw, "repair_id")
        db_ids = get_database_ids(
            cursor, "Repair", "repair_id"
        )

        missing_original_ids = raw_ids - db_ids
        additional_ids = db_ids - raw_ids

        # Compare intentional mismatch against ground truth.
        cursor.execute("""
            SELECT entity_id
            FROM DataAnomaly
            WHERE issue_type =
                'REPAIR_WITHOUT_VALID_ASSET_INSPECTION'
              AND entity_type = 'Repair'
              AND ground_truth = 'ANOMALY'
        """)
        expected_mismatch_ids = {
            row[0] for row in cursor.fetchall()
        }

        mismatch_matches_ground_truth = (
            repair_asset_mismatches == expected_mismatch_ids
        )

        print("1. Total Repair Records:", total)
        print("2. Unique Repair IDs:", unique_ids)
        print("3. Unique Repaired Assets:", unique_assets)
        print("4. Invalid Repair Costs:", invalid_costs)
        print("5. Invalid Repair Statuses:", invalid_statuses)
        print("6. Completed Repairs Without End Date:",
              completed_without_end_date)
        print("7. Unfinished Repairs With End Date:",
              unfinished_with_end_date)
        print("8. Repairs Without Failed Inspection:",
              len(repairs_without_failed_inspection))
        print("9. Repairs Before Inspection:",
              repairs_before_inspection)
        print("10. Repair/Inspection Asset Mismatches:",
              len(repair_asset_mismatches))
        print("    Matches Ground Truth:",
              mismatch_matches_ground_truth)
        print("11. Foreign Key Errors:", fk_errors)
        print("12. Original CSV Records:", len(raw))
        print("    Original IDs Missing From Database:",
              len(missing_original_ids))
        print("    Additional Generated/Injected Records:",
              len(additional_ids))

        passed = (
            total == EXPECTED_REPAIRS
            and unique_ids == total
            and invalid_costs == 0
            and invalid_statuses == 0
            and completed_without_end_date == 0
            and unfinished_with_end_date == 0
            and repairs_before_inspection == 0
            and fk_errors == 0
            and len(missing_original_ids) == 0
            and len(additional_ids) == 1
            and mismatch_matches_ground_truth
        )

        if passed:
            print("\nSUCCESS: Repair Structure Validated!")
            print(
                "Note: Intentional repair/inspection mismatch "
                "matches ground truth."
            )
        else:
            print("\nWARNING: Repair Validation Requires Investigation!")

    finally:
        connection.close()


# ============================================================
# 7. GROUND-TRUTH ANOMALY VALIDATION
# ============================================================

def validate_ground_truth():

    print("\n===== GROUND TRUTH ANOMALY VALIDATION =====")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT issue_type, entity_type, entity_id, ground_truth
            FROM DataAnomaly
        """)

        rows = cursor.fetchall()

        actual_types = {
            row[0] for row in rows
            if row[3] == "ANOMALY"
        }

        print("1. Ground Truth Records:", len(rows))
        print("2. Expected Anomaly Categories:",
              sorted(EXPECTED_ANOMALIES))
        print("3. Actual Anomaly Categories:",
              sorted(actual_types))

        missing_categories = EXPECTED_ANOMALIES - actual_types
        unexpected_categories = actual_types - EXPECTED_ANOMALIES

        print("4. Missing Categories:",
              sorted(missing_categories))
        print("5. Unexpected Categories:",
              sorted(unexpected_categories))

        passed = (
            len(rows) == 5
            and actual_types == EXPECTED_ANOMALIES
        )

        if passed:
            print("\nSUCCESS: Ground Truth Validation Passed!")
        else:
            print("\nWARNING: Ground Truth Validation Requires Investigation!")

    finally:
        connection.close()


# ============================================================
# 8. RUN ALL VALIDATIONS
# ============================================================

def run_all_validations():

    print("\n" + "=" * 65)
    print("       RETURNABLE ASSET MANAGEMENT SYSTEM")
    print("                 FINAL DATA AUDIT")
    print("=" * 65)

    validation_functions = [
        validate_reusable_assets,
        validate_shipments,
        validate_custody_events,
        validate_return_authorizations,
        validate_inspections,
        validate_repairs,
        validate_ground_truth
    ]

    for validation_function in validation_functions:
        try:
            validation_function()
        except Exception as error:
            print(
                f"\nERROR in {validation_function.__name__}: {error}"
            )

    print("\n" + "=" * 65)
    print("                 VALIDATION RUN COMPLETED")
    print("=" * 65)


if __name__ == "__main__":
    run_all_validations()
