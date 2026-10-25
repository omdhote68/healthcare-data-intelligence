"""Central settings for the project.

Keeping these in one place means we can change behaviour
(e.g. add a new column alias) without hunting through the code.
"""

from pathlib import Path

# --- Folder locations -------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
LOG_DIR = PROJECT_ROOT / "logs"
SAMPLE_FILE = DATA_DIR / "sample_practices.csv"

# --- The standard columns every dataset is converted into ---------------
STANDARD_COLUMNS = [
    "practice_name",
    "doctor_name",
    "specialty",
    "city",
    "phone",
    "website",
    "source_url",
]

# --- Alternative column names we recognise -----------------------------
# Comparisons ignore case, spaces, underscores and symbols.
COLUMN_ALIASES = {
    "practice_name": ["practicename", "practice", "clinicname", "clinic", "hospitalname", "name"],
    "doctor_name": ["doctorname", "doctor", "physician", "physicianname", "drname", "dr"],
    "specialty": ["specialty", "speciality", "specialization", "specialisation", "department"],
    "city": ["city", "town", "location"],
    "phone": ["phone", "phonenumber", "telephone", "tel", "contactnumber", "mobile"],
    "website": ["website", "web", "url", "site", "websiteurl"],
    "source_url": ["sourceurl", "sourcelink", "reference"],
}

# Columns a record needs to be considered "complete".
# (doctor_name is optional: many practices do not list individual doctors.)
REQUIRED_FOR_COMPLETE = ["practice_name", "specialty", "city", "phone"]

# Columns that are cleaned as plain text with tidy capitalisation.
TEXT_COLUMNS = ["practice_name", "doctor_name", "specialty", "city"]

# --- Limits and thresholds ---------------------------------------------
MAX_ROWS = 20000            # safety limit for the demo app
PHONE_MIN_DIGITS = 7
PHONE_MAX_DIGITS = 15       # international standard maximum
FUZZY_THRESHOLD = 0.88      # name similarity (0-1) for "potential duplicate"
MAX_FUZZY_GROUP = 3000      # skip fuzzy matching inside huge city groups

# --- Severity labels used in the issue report ----------------------------
SEVERITY_ORDER = ["high", "medium", "low", "info"]

# Every exported record carries this label so nobody mistakes
# "passed format checks" for "verified as correct".
VERIFICATION_LABEL = "Not verified - automated format checks only"

# --- AI settings ---------------------------------------------------------
DEFAULT_AI_MODEL = "claude-sonnet-4-6"
MAX_AI_ITEMS = 100          # max unique records sent for AI categorisation
