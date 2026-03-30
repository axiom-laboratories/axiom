#!/usr/bin/env python3
"""list_licences.py — Audit query script for issued Axiom licences.

Reads all YAML records from licenses/issued/*.yml (relative to the axiom-licenses/
repo root) and prints a formatted table sorted by expiry ascending (soonest first).

Usage (from axiom-licenses/ directory):
    python tools/list_licences.py          # table output
    python tools/list_licences.py --json   # machine-readable JSON
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


# Column widths
_COL_CUSTOMER = 20
_COL_TIER = 6
_COL_NODES = 8
_COL_ISSUED_AT = 12
_COL_EXPIRY = 12
_COL_ISSUED_BY = 30


def load_records(issued_dir: Path) -> list:
    """Load all YAML records from the issued/ directory. Returns a list of dicts."""
    if not issued_dir.exists():
        return []
    records = []
    for yml_file in issued_dir.glob("*.yml"):
        try:
            data = yaml.safe_load(yml_file.read_text())
            if isinstance(data, dict):
                records.append(data)
        except yaml.YAMLError as exc:
            print(f"Warning: could not parse {yml_file.name}: {exc}", file=sys.stderr)
    return records


def sort_records(records: list) -> list:
    """Sort records by expiry ascending (soonest-to-expire first)."""
    return sorted(records, key=lambda r: r.get("expiry", "9999-99-99"))


def print_table(records: list) -> None:
    """Print a fixed-width table of licence records to stdout."""
    header = (
        f"{'CUSTOMER':<{_COL_CUSTOMER}} "
        f"{'TIER':<{_COL_TIER}} "
        f"{'NODES':<{_COL_NODES}} "
        f"{'ISSUED_AT':<{_COL_ISSUED_AT}} "
        f"{'EXPIRY':<{_COL_EXPIRY}} "
        f"{'ISSUED_BY':<{_COL_ISSUED_BY}}"
    )
    separator = (
        f"{'-' * _COL_CUSTOMER} "
        f"{'-' * _COL_TIER} "
        f"{'-' * _COL_NODES} "
        f"{'-' * _COL_ISSUED_AT} "
        f"{'-' * _COL_EXPIRY} "
        f"{'-' * _COL_ISSUED_BY}"
    )
    print(header)
    print(separator)
    for r in records:
        customer = str(r.get("customer_id", ""))[:_COL_CUSTOMER]
        tier = str(r.get("tier", ""))[:_COL_TIER]
        nodes = str(r.get("node_limit", ""))[:_COL_NODES]
        issued_at = str(r.get("issued_at", ""))[:_COL_ISSUED_AT]
        expiry = str(r.get("expiry", ""))[:_COL_EXPIRY]
        issued_by = str(r.get("issued_by", "unknown"))[:_COL_ISSUED_BY]
        print(
            f"{customer:<{_COL_CUSTOMER}} "
            f"{tier:<{_COL_TIER}} "
            f"{nodes:<{_COL_NODES}} "
            f"{issued_at:<{_COL_ISSUED_AT}} "
            f"{expiry:<{_COL_EXPIRY}} "
            f"{issued_by:<{_COL_ISSUED_BY}}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="List all issued Axiom licences from the YAML audit records."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print records as JSON instead of a table",
    )
    args = parser.parse_args()

    # Resolve issued/ directory relative to the axiom-licenses repo root
    # Script lives at axiom-licenses/tools/list_licences.py
    # So parent.parent is axiom-licenses/
    repo_root = Path(__file__).parent.parent
    issued_dir = repo_root / "licenses" / "issued"

    records = load_records(issued_dir)
    # Filter out empty records (e.g. .gitkeep loading as None)
    records = [r for r in records if r]

    if not records:
        if args.as_json:
            print("[]")
        else:
            print("No licences issued yet.")
        return

    sorted_recs = sort_records(records)

    if args.as_json:
        print(json.dumps(sorted_recs, indent=2, default=str))
    else:
        print_table(sorted_recs)


if __name__ == "__main__":
    main()
