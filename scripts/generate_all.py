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
     "start_year": 1860, "founders": 8, "gen_span": 17,
     "min_children": 2, "max_children": 4, "external_spouse_ratio": 0.92, "male_birth_ratio": 0.64,
     "desc": "~500 members (dev/debug)"},
    {"name": "medium", "dir": OUT / "medium", "target": 5000,  "seed": 2026,
     "gid": 2, "mid0": 20000, "marr0": 20000,
     "start_year": 1720, "founders": 10, "gen_span": 18,
     "min_children": 2, "max_children": 4, "external_spouse_ratio": 0.90, "male_birth_ratio": 0.63,
     "desc": "~5,000 members (functional test)"},
    {"name": "large",  "dir": OUT / "large",  "target": 50000, "seed": 20260108,
     "gid": 3, "mid0": 30000, "marr0": 30000,
     "start_year": 1600, "founders": 12, "gen_span": 18,
     "min_children": 2, "max_children": 4, "external_spouse_ratio": 0.88, "male_birth_ratio": 0.62,
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
            "--min-children", str(ds["min_children"]),
            "--max-children", str(ds["max_children"]),
            "--external-spouse-ratio", str(ds["external_spouse_ratio"]),
            "--male-birth-ratio", str(ds["male_birth_ratio"]),
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
