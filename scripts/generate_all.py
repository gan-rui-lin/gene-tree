"""Generate small / medium / large family datasets for dev, test, and stress."""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "generate_family_csv.py"
BASE = Path(__file__).parent.parent / "sql" / "generated"

DATASETS = [
    {
        "name": "small",
        "dir": BASE / "small",
        "desc": "1 genealogy, ~50 members (dev/debug)",
        "args": [
            "--genealogy-count", "1",
            "--generations", "7",
            "--min-children", "3", "--max-children", "4",
            "--gender-ratio", "0.5",
            "--marriage-probability", "0.95",
            "--alive-probability", "0.4",
            "--seed", "42",
        ],
    },
    {
        "name": "medium",
        "dir": BASE / "medium",
        "desc": "3 genealogies, ~1,000 members (functional test)",
        "args": [
            "--genealogy-count", "3",
            "--generations", "7",
            "--min-children", "4", "--max-children", "5",
            "--gender-ratio", "0.5",
            "--marriage-probability", "0.9",
            "--alive-probability", "0.3",
            "--seed", "2026",
        ],
    },
    {
        "name": "large",
        "dir": BASE / "large",
        "desc": "10 genealogies, 10,000+ members (performance stress)",
        "args": [
            "--genealogy-count", "10",
            "--generations", "8",
            "--min-children", "4", "--max-children", "6",
            "--gender-ratio", "0.5",
            "--marriage-probability", "0.85",
            "--alive-probability", "0.25",
            "--seed", "20260108",
        ],
    },
]


def run():
    python = sys.executable
    for ds in DATASETS:
        out_dir = ds["dir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [python, str(SCRIPT), "--out-dir", str(out_dir)] + ds["args"]
        print(f"\n{'='*50}")
        print(f"[{ds['name']}] {ds['desc']}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr}")
        else:
            for line in result.stdout.strip().splitlines():
                print(f"  {line}")
    print(f"\n{'='*50}")
    print("All datasets generated.")


if __name__ == "__main__":
    run()
