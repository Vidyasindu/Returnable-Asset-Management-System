
-- =====================================================
-- RETURNABLE ASSET MANAGEMENT SYSTEM
-- DATABASE SCHEMA
-- =====================================================

PRAGMA foreign_keys = ON;

-- 1. ASSET TYPE
CREATE TABLE IF NOT EXISTS AssetType (
    asset_type_id TEXT PRIMARY KEY,
    asset_type_name TEXT NOT NULL,
    return_period_days INTEGER NOT NULL
        CHECK (return_period_days > 0),
    deposit_amount REAL NOT NULL
        CHECK (deposit_amount >= 0),
    repairable INTEGER NOT NULL
        CHECK (repairable IN (0, 1)),
    created_at TEXT NOT NULL
);

-- 2. OWNER
CREATE TABLE IF NOT EXISTS Owner (
    owner_id TEXT PRIMARY KEY,
    owner_name TEXT NOT NULL,
    owner_type TEXT NOT NULL
        CHECK (owner_type IN ('SUPPLIER', 'CUSTOMER', 'LOGISTICS')),
    contact_email TEXT,
    created_at TEXT NOT NULL
);

-- 3. LOCATION
CREATE TABLE IF NOT EXISTS Location (
    location_id TEXT PRIMARY KEY,
    location_name TEXT NOT NULL,
    location_type TEXT NOT NULL
        CHECK (location_type IN (
            'WAREHOUSE', 'CUSTOMER', 'SUPPLIER', 'REPAIR_CENTER'
        )),
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 4. REUSABLE ASSET
CREATE TABLE IF NOT EXISTS ReusableAsset (
    asset_id TEXT PRIMARY KEY,
    asset_type_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    current_location_id TEXT,
    asset_status TEXT NOT NULL
        CHECK (asset_status IN (
            'AVAILABLE', 'IN_TRANSIT', 'WITH_CUSTOMER',
            'OVERDUE', 'DAMAGED', 'UNDER_REPAIR', 'LOST'
        )),
    purchase_date TEXT NOT NULL,
    deposit_amount REAL NOT NULL
        CHECK (deposit_amount >= 0),
    created_at TEXT NOT NULL,

    FOREIGN KEY (asset_type_id)
        REFERENCES AssetType(asset_type_id),

    FOREIGN KEY (owner_id)
        REFERENCES Owner(owner_id),

    FOREIGN KEY (current_location_id)
        REFERENCES Location(location_id)
);

-- 5. SHIPMENT
CREATE TABLE IF NOT EXISTS Shipment (
    shipment_id TEXT PRIMARY KEY,
    from_location_id TEXT NOT NULL,
    to_location_id TEXT NOT NULL,
    carrier_owner_id TEXT,
    dispatch_date TEXT NOT NULL,
    expected_delivery_date TEXT NOT NULL,
    shipment_status TEXT NOT NULL
        CHECK (shipment_status IN (
            'CREATED', 'DISPATCHED', 'IN_TRANSIT',
            'DELIVERED', 'CANCELLED'
        )),

    FOREIGN KEY (from_location_id)
        REFERENCES Location(location_id),

    FOREIGN KEY (to_location_id)
        REFERENCES Location(location_id),

    FOREIGN KEY (carrier_owner_id)
        REFERENCES Owner(owner_id),

    CHECK (expected_delivery_date >= dispatch_date)
);

-- 6. SHIPMENT ASSET (BRIDGE TABLE)
CREATE TABLE IF NOT EXISTS ShipmentAsset (
    shipment_asset_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    removed_at TEXT,

    FOREIGN KEY (shipment_id)
        REFERENCES Shipment(shipment_id),

    FOREIGN KEY (asset_id)
        REFERENCES ReusableAsset(asset_id),

    CHECK (
        removed_at IS NULL OR removed_at >= assigned_at
    )
);

-- 7. CUSTODY EVENT
CREATE TABLE IF NOT EXISTS CustodyEvent (
    custody_event_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    shipment_id TEXT,
    actor_owner_id TEXT,
    from_location_id TEXT,
    to_location_id TEXT,
    event_type TEXT NOT NULL
        CHECK (event_type IN (
            'DISPATCH', 'RECEIVED', 'TRANSFER', 'RETURN'
        )),
    event_timestamp TEXT NOT NULL,

    FOREIGN KEY (asset_id)
        REFERENCES ReusableAsset(asset_id),

    FOREIGN KEY (shipment_id)
        REFERENCES Shipment(shipment_id),

    FOREIGN KEY (actor_owner_id)
        REFERENCES Owner(owner_id),

    FOREIGN KEY (from_location_id)
        REFERENCES Location(location_id),

    FOREIGN KEY (to_location_id)
        REFERENCES Location(location_id)
);

-- 8. RETURN AUTHORIZATION
CREATE TABLE IF NOT EXISTS ReturnAuthorization (
    rma_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    request_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    return_date TEXT,
    return_status TEXT NOT NULL
        CHECK (return_status IN (
            'PENDING', 'APPROVED', 'RETURNED', 'CANCELLED'
        )),

    FOREIGN KEY (asset_id)
        REFERENCES ReusableAsset(asset_id),

    CHECK (due_date >= request_date),
    CHECK (return_date IS NULL OR return_date >= request_date)
);

-- 9. INSPECTION
CREATE TABLE IF NOT EXISTS Inspection (
    inspection_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    inspection_date TEXT NOT NULL,
    asset_condition TEXT NOT NULL
        CHECK (asset_condition IN ('GOOD', 'DAMAGED', 'CRITICAL')),
    inspection_result TEXT NOT NULL
        CHECK (inspection_result IN ('PASS', 'FAIL')),

    FOREIGN KEY (asset_id)
        REFERENCES ReusableAsset(asset_id)
);

-- 10. REPAIR
CREATE TABLE IF NOT EXISTS Repair (
    repair_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    inspection_id TEXT NOT NULL,
    repair_start_date TEXT NOT NULL,
    repair_end_date TEXT,
    repair_cost REAL NOT NULL
        CHECK (repair_cost >= 0),
    repair_status TEXT NOT NULL
        CHECK (repair_status IN (
            'PENDING', 'IN_PROGRESS', 'COMPLETED'
        )),

    FOREIGN KEY (asset_id)
        REFERENCES ReusableAsset(asset_id),

    FOREIGN KEY (inspection_id)
        REFERENCES Inspection(inspection_id),

    CHECK (
        repair_end_date IS NULL OR repair_end_date >= repair_start_date
    )
);

-- 11. DEPOSIT LEDGER
CREATE TABLE IF NOT EXISTS DepositLedger (
    transaction_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL
        CHECK (transaction_type IN (
            'CHARGE', 'REFUND', 'DEDUCTION'
        )),
    amount REAL NOT NULL
        CHECK (amount > 0),
    transaction_date TEXT NOT NULL,
    reference_id TEXT,

    FOREIGN KEY (asset_id)
        REFERENCES ReusableAsset(asset_id)
);

-- =====================================================
-- INDEXES
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_asset_status
ON ReusableAsset(asset_status);

CREATE INDEX IF NOT EXISTS idx_custody_asset
ON CustodyEvent(asset_id);

CREATE INDEX IF NOT EXISTS idx_custody_timestamp
ON CustodyEvent(event_timestamp);

CREATE INDEX IF NOT EXISTS idx_shipment_status
ON Shipment(shipment_status);

CREATE INDEX IF NOT EXISTS idx_rma_asset
ON ReturnAuthorization(asset_id);

CREATE INDEX IF NOT EXISTS idx_ledger_asset
ON DepositLedger(asset_id);
