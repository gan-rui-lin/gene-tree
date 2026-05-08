"""Generate small / medium / large family datasets.

Each dataset is a separate genealogy with unique genealogy_id and
non-overlapping member_id ranges, so all three can be imported
into the same database simultaneously.
"""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "generate_family_csv.py"
OUT = Path(__file__).parent.parent / "sql" / "generated"

DATASETS = [
    {"name": "small",  "dir": OUT / "small",  "target": 500,   "seed": 42,
     "gid": 1, "mid0": 10000, "marr0": 10000,
     "start_year": 1920, "founders": 30, "gen_span": 15,
     "desc": "~500 members (dev/debug)"},
    {"name": "medium", "dir": OUT / "medium", "target": 5000,  "seed": 2026,
     "gid": 2, "mid0": 20000, "marr0": 20000,
     "start_year": 1810, "founders": 20, "gen_span": 20,
     "desc": "~5,000 members (functional test)"},
    {"name": "large",  "dir": OUT / "large",  "target": 50000, "seed": 20260108,
     "gid": 3, "mid0": 30000, "marr0": 30000,
     "start_year": 1780, "founders": 60, "gen_span": 20,
     "desc": "~50,000 members (performance stress)"},
]


def run():
    py = sys.executable
    for ds in DATASETS:
        ds["dir"].mkdir(parents=True, exist_ok=True)
        cmd = [
            py, str(SCRIPT),
            "--out-dir", str(ds["dir"]),
            "--target", str(ds["target"]),
            "--seed", str(ds["seed"]),
            "--genealogy-id", str(ds["gid"]),
            "--start-member-id", str(ds["mid0"]),
            "--start-marriage-id", str(ds["marr0"]),
            "--start-year", str(ds["start_year"]),
            "--founders", str(ds["founders"]),
            "--gen-span", str(ds["gen_span"]),
        ]
        print(f"\n[{ds['name']}] {ds['desc']}")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ERROR: {r.stderr}")
        else:
            for line in r.stdout.strip().splitlines():
                print(f"  {line}")


if __name__ == "__main__":
    run()
