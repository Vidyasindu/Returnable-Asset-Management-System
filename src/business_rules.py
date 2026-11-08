
import sqlite3


def get_asset_lifecycle(db_path):
    """Derive asset lifecycle from inspection and repair records."""

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    query = """
    SELECT
        a.asset_id,
        CASE
            WHEN a.asset_status = 'LOST' THEN 'LOST'
            WHEN a.asset_status = 'OVERDUE' THEN 'OVERDUE'
            WHEN r.repair_status = 'IN_PROGRESS' THEN 'UNDER_REPAIR'
            WHEN r.repair_status = 'PENDING' THEN 'DAMAGED'
            WHEN i.inspection_result = 'PASS' THEN 'AVAILABLE'
            ELSE 'DAMAGED'
        END AS lifecycle_status
    FROM ReusableAsset a
    LEFT JOIN Inspection i
        ON i.asset_id = a.asset_id
        AND i.inspection_date = (
            SELECT MAX(i2.inspection_date)
            FROM Inspection i2
            WHERE i2.asset_id = a.asset_id
        )
    LEFT JOIN Repair r
        ON r.asset_id = a.asset_id
        AND r.repair_id = (
            SELECT MAX(r2.repair_id)
            FROM Repair r2
            WHERE r2.asset_id = a.asset_id
        )
    """

    cursor.execute(query)
    results = cursor.fetchall()

    connection.close()
    return results


def get_asset_status_summary(db_path):
    """Return the number of assets in each lifecycle status."""

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT asset_status, COUNT(*)
        FROM ReusableAsset
        GROUP BY asset_status
    """)

    results = dict(cursor.fetchall())
    connection.close()

    return results
