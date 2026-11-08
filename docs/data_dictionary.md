# Returnable Asset Management System – Data Dictionary

## 1. AssetType
Purpose: Stores different categories of reusable assets.

| Column | Data Type | Required | Description |
|---|---|---|---|
| asset_type_id | VARCHAR(20) | Yes | Unique asset type ID (PK) |
| asset_type_name | VARCHAR(100) | Yes | Name of asset type |
| return_period_days | INTEGER | Yes | Allowed return period |
| deposit_amount | DECIMAL(10,2) | Yes | Deposit amount |
| repairable | BOOLEAN | Yes | Whether asset can be repaired |
| created_at | DATETIME | Yes | Record creation date |

## 2. Owner
Purpose: Stores asset owners and business parties.

| Column | Data Type | Required | Description |
|---|---|---|---|
| owner_id | VARCHAR(20) | Yes | Unique owner ID (PK) |
| owner_name | VARCHAR(100) | Yes | Owner name |
| owner_type | VARCHAR(30) | Yes | SUPPLIER, CUSTOMER, LOGISTICS |
| contact_email | VARCHAR(100) | No | Contact email |
| created_at | DATETIME | Yes | Record creation date |

## 3. Location
Purpose: Stores warehouses, suppliers and customer locations.

| Column | Data Type | Required | Description |
|---|---|---|---|
| location_id | VARCHAR(20) | Yes | Unique location ID (PK) |
| location_name | VARCHAR(100) | Yes | Location name |
| location_type | VARCHAR(30) | Yes | WAREHOUSE, CUSTOMER, SUPPLIER, REPAIR_CENTER |
| city | VARCHAR(50) | Yes | City |
| state | VARCHAR(50) | Yes | State |
| created_at | DATETIME | Yes | Record creation date |

## 4. ReusableAsset
Purpose: Stores information about individual reusable assets.

| Column | Data Type | Required | Description |
|---|---|---|---|
| asset_id | VARCHAR(30) | Yes | Unique asset ID (PK) |
| asset_type_id | VARCHAR(20) | Yes | Asset type reference (FK) |
| owner_id | VARCHAR(20) | Yes | Owner reference (FK) |
| current_location_id | VARCHAR(20) | No | Current location reference (FK) |
| asset_status | VARCHAR(30) | Yes | Current lifecycle status |
| purchase_date | DATE | Yes | Purchase date |
| deposit_amount | DECIMAL(10,2) | Yes | Asset deposit |
| created_at | DATETIME | Yes | Record creation date |

## 5. Shipment
Purpose: Stores shipment and transportation details.

| Column | Data Type | Required | Description |
|---|---|---|---|
| shipment_id | VARCHAR(30) | Yes | Unique shipment ID (PK) |
| from_location_id | VARCHAR(20) | Yes | Dispatch location (FK) |
| to_location_id | VARCHAR(20) | Yes | Destination location (FK) |
| carrier_owner_id | VARCHAR(20) | No | Carrier reference (FK) |
| dispatch_date | DATETIME | Yes | Shipment dispatch time |
| expected_delivery_date | DATETIME | Yes | Expected delivery time |
| shipment_status | VARCHAR(30) | Yes | Shipment status |

## 6. CustodyEvent
Purpose: Records asset movements and custody changes.

| Column | Data Type | Required | Description |
|---|---|---|---|
| custody_event_id | VARCHAR(50) | Yes | Unique custody event ID (PK) |
| asset_id | VARCHAR(30) | Yes | Asset reference (FK) |
| shipment_id | VARCHAR(30) | No | Shipment reference (FK) |
| actor_owner_id | VARCHAR(20) | No | Responsible actor (FK) |
| from_location_id | VARCHAR(20) | No | Previous location (FK) |
| to_location_id | VARCHAR(20) | No | New location (FK) |
| event_type | VARCHAR(30) | Yes | DISPATCH, RECEIVED, TRANSFER, RETURN |
| event_timestamp | DATETIME | Yes | Event date and time |

## 7. ReturnAuthorization
Purpose: Stores approved asset return requests.

| Column | Data Type | Required | Description |
|---|---|---|---|
| rma_id | VARCHAR(30) | Yes | Unique return authorization ID (PK) |
| asset_id | VARCHAR(30) | Yes | Asset reference (FK) |
| request_date | DATETIME | Yes | Return request date |
| due_date | DATETIME | Yes | Expected return date |
| return_date | DATETIME | No | Actual return date |
| return_status | VARCHAR(30) | Yes | PENDING, APPROVED, RETURNED, CANCELLED |

## 8. Inspection
Purpose: Records the condition of returned assets.

| Column | Data Type | Required | Description |
|---|---|---|---|
| inspection_id | VARCHAR(30) | Yes | Unique inspection ID (PK) |
| asset_id | VARCHAR(30) | Yes | Asset reference (FK) |
| inspection_date | DATETIME | Yes | Inspection date |
| asset_condition | VARCHAR(30) | Yes | GOOD, DAMAGED, CRITICAL |
| inspection_result | VARCHAR(30) | Yes | PASS, FAIL |

## 9. Repair
Purpose: Stores repair activities.

| Column | Data Type | Required | Description |
|---|---|---|---|
| repair_id | VARCHAR(30) | Yes | Unique repair ID (PK) |
| asset_id | VARCHAR(30) | Yes | Asset reference (FK) |
| inspection_id | VARCHAR(30) | Yes | Inspection reference (FK) |
| repair_start_date | DATETIME | Yes | Repair start date |
| repair_end_date | DATETIME | No | Repair completion date |
| repair_cost | DECIMAL(10,2) | Yes | Repair cost |
| repair_status | VARCHAR(30) | Yes | PENDING, IN_PROGRESS, COMPLETED |

## 10. DepositLedger
Purpose: Records all deposit charges, refunds and adjustments.

| Column | Data Type | Required | Description |
|---|---|---|---|
| transaction_id | VARCHAR(30) | Yes | Unique transaction ID (PK) |
| asset_id | VARCHAR(30) | Yes | Asset reference (FK) |
| transaction_type | VARCHAR(30) | Yes | CHARGE, REFUND, DEDUCTION |
| amount | DECIMAL(10,2) | Yes | Transaction amount |
| transaction_date | DATETIME | Yes | Transaction date |
| reference_id | VARCHAR(30) | No | Related transaction or business reference |

## 11. ShipmentAsset

Purpose: Connects shipments with reusable assets. One shipment can contain multiple assets, and one asset can travel through multiple shipments.

| Column | Data Type | Required | Description |
|---|---|---|---|
| shipment_asset_id | VARCHAR(30) | Yes | Unique assignment ID (PK) |
| shipment_id | VARCHAR(30) | Yes | Shipment reference (FK) |
| asset_id | VARCHAR(30) | Yes | Asset reference (FK) |
| assigned_at | DATETIME | Yes | Asset assignment date |
| removed_at | DATETIME | No | Date asset was removed from shipment |

Constraints:
- shipment_asset_id must be unique.
- shipment_id must reference an existing shipment.
- asset_id must reference an existing reusable asset.
- One asset must not be assigned to two overlapping active shipments.
- The same asset may appear in multiple shipments over time, provided the assignments do not overlap.

---

## General Data Rules

<!-- 1. All primary keys must be unique.
2. Foreign keys must reference existing records.
3. Asset IDs must follow ASSET-0000001 format.
4. Shipment IDs must follow SHP-2026-000001 format.
5. Return authorization IDs must follow RMA-2026-000001 format.
6. Repair IDs must follow REP-2026-000001 format.
7. Deposit amounts cannot be negative.
8. Return dates cannot precede dispatch dates.
9. Historical events must never be overwritten.
10. All derived statuses must be calculated using business rules. -->