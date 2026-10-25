"""Command-line runner (no dashboard needed).

Examples:
    python run_pipeline.py                         # uses the built-in sample file
    python run_pipeline.py data/my_file.xlsx
    python run_pipeline.py data/my_file.csv --ai   # needs ANTHROPIC_API_KEY
"""

import argparse
import sys

from dotenv import load_dotenv

from src.config import OUTPUT_DIR, SAMPLE_FILE
from src.exporter import save_outputs
from src.loader import LoaderError
from src.logger import get_logger
from src.pipeline import run_pipeline

logger = get_logger()


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Healthcare directory data pipeline")
    parser.add_argument("file", nargs="?", default=str(SAMPLE_FILE), help="CSV or XLSX file")
    parser.add_argument("--ai", action="store_true", help="use the AI API (needs a key)")
    parser.add_argument("--out", default=str(OUTPUT_DIR), help="output folder")
    args = parser.parse_args()

    try:
        result = run_pipeline(args.file, use_ai=args.ai)
        paths = save_outputs(result, args.out)
    except LoaderError as exc:
        logger.error("Could not process file: %s", exc)
        print(f"\nERROR: {exc}")
        return 1
    except OSError as exc:
        print(f"\nERROR: could not write output files: {exc}")
        return 1

    print("\nResults")
    for key, value in result.metrics.items():
        print(f"  {key:30s} {value}")
    print(f"\nAI mode: {result.ai.mode}")
    print("\nFiles written:")
    for path in paths.values():
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
