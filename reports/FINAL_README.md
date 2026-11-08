
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

- Assets: 20000
- Shipments: 10000
- Custody Events: 101004
- Return Authorizations: 21000
- Inspections: 23483
- Repairs: 4953
- Deposit Transactions: 42030

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

Random seed: 20261022

Scenario evaluation date: 2027-04-26T00:00:00

## Run

python src/complete_project.py

## Dashboard

Open dashboard/index.html in a browser.

## Validation

See reports/validation_summary.json.

## Ground Truth

See data/ground_truth/ground_truth.csv.
