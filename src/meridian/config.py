import os
from pathlib import Path
from datetime import date

# Root of the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Default starter-kit directories
STARTER_KIT_DIR = BASE_DIR / "starter-kit"
DATA_DIR = Path(os.environ.get("MERIDIAN_DATA_DIR", str(STARTER_KIT_DIR / "data")))
ENVIRONMENTS_DIR = Path(os.environ.get("MERIDIAN_ENV_DIR", str(STARTER_KIT_DIR / "environments")))
CONTRACTS_DIR = Path(os.environ.get("MERIDIAN_CONTRACTS_DIR", str(STARTER_KIT_DIR / "contracts")))

# Current environment: 'dev', 'staging', or 'prod'
CURRENT_ENV = os.environ.get("MERIDIAN_ENV", "dev").lower()

# Reference date for relative periods (end of data window per assignment: 2026-09-28)
REFERENCE_DATE = date.fromisoformat(os.environ.get("MERIDIAN_REFERENCE_DATE", "2026-09-28"))

# SQLite database path
DATABASE_URL = os.environ.get("MERIDIAN_DB_URL", f"sqlite:///{BASE_DIR / f'meridian_{CURRENT_ENV}.db'}")
SQLITE_PATH = Path(os.environ.get("MERIDIAN_SQLITE_PATH", str(BASE_DIR / f"meridian_{CURRENT_ENV}.db")))
