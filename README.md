# Returnable Asset Management System

## Project Overview

The Returnable Asset Management System is a Python and SQLite-based solution designed to track reusable assets across suppliers, warehouses, customers, and logistics operations.

It maintains asset records, shipment details, custody events, return authorizations, inspections, repairs, and deposit transactions. The system also identifies operational anomalies and generates project metrics and reports.

## Key Features

- **Asset Management:** Track reusable assets and their lifecycle statuses.
- **Shipment Tracking:** Monitor shipments and asset assignments.
- **Custody Tracking:** Maintain event-level asset movement history.
- **Return Management:** Manage return authorizations and asset returns.
- **Inspection and Repair:** Track asset conditions and repair activities.
- **Deposit Management:** Record charges, deductions, and refunds.
- **Anomaly Detection:** Identify five deliberately injected operational anomalies.
- **Data Validation:** Check data integrity and foreign key constraints.
- **Metrics and Reporting:** Generate summary metrics and validation reports.
- **Dashboard:** View asset statistics and detected anomalies.

## Technology Stack

- Python
- SQLite
- Pandas
- NumPy
- Matplotlib
- Seaborn
- Faker
- SQLAlchemy
- HTML

## Project Structure

```text
yottaflex_ai_code_challenge/
|
|-- data/
|   |-- raw/
|   |-- processed/
|   |-- ground_truth/
|
|-- database/
|   |-- returnable_assets.db
|   |-- seed.sql
|
|-- dashboard/
|   |-- index.html
|
|-- src/
|   |-- config.py
|   |-- generate_master_data.py
|   |-- generate_transactions.py
|   |-- generate_custody_events.py
|   |-- generate_return_authorizations.py
|   |-- generate_inspections.py
|   |-- generate_repairs.py
|   |-- business_rules.py
|   |-- anomaly_detection.py
|   |-- validation.py
|   |-- calculate_metrics.py
|   |-- complete_project.py
|
|-- reports/
|-- tests/
|-- requirements.txt
|-- .gitignore
|-- README.md
```

## Installation

Clone the repository:

```bash
git clone <your-github-repository-url>
cd yottaflex_ai_code_challenge
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Project

Run anomaly detection:

```bash
python src/anomaly_detection.py
```

Calculate project metrics:

```bash
python src/calculate_metrics.py
```

## Injected Anomalies

The system includes five deliberately injected anomalies:

1. Same asset recorded at multiple locations simultaneously.
2. Return event occurring before dispatch.
3. Duplicate deposit refund.
4. Repair linked to an inspection belonging to another asset.
5. Custody event with a missing actor.

## Dashboard

Open `dashboard/index.html` in a web browser to view asset statistics, shipment information, and detected anomalies.

## Database

The project uses SQLite to maintain structured records and relationships across asset management, logistics, custody, inspection, repair, and deposit transactions.

## Evaluation Metrics

The project calculates:

- True Positives (TP)
- False Positives (FP)
- False Negatives (FN)
- Precision
- Recall
- F1-score
- Foreign key validation errors

**Note:** The reported anomaly detection scores are based on the five deliberately injected anomalies in the generated dataset. They should not be interpreted as general real-world model performance.

## Author

Developed as part of the Yottaflex AI Code Challenge.