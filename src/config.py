
from pathlib import Path

# ==========================================
# PROJECT CONFIGURATION
# ==========================================

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

# SQLite database location
DB_PATH = BASE_DIR / "database" / "returnable_assets.db"


# ==========================================
# DATA STORAGE CONFIGURATION
# ==========================================

# Raw generated data
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Processed data
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

# Ground truth data
GROUND_TRUTH_DIR = BASE_DIR / "data" / "ground_truth"


# ==========================================
# DATA GENERATION CONFIGURATION
# ==========================================

# Fixed random seed for reproducibility
RANDOM_SEED = 20261022

# Total reusable assets to generate
TOTAL_ASSETS = 20_000

# Total shipments to generate (future step)
TOTAL_SHIPMENTS = 10_000

# Total custody events to generate (future step)
TOTAL_CUSTODY_EVENTS = 100_000


# ==========================================
# CREATE REQUIRED DIRECTORIES
# ==========================================

RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)
