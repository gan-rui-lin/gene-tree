import argparse
import csv
import random
from pathlib import Path


def new_member(member_id, genealogy_id, generation, gender=None):
    if gender is None:
        gender = random.choice(["M", "F"])
    return {
        "member_id": member_id,
        "genealogy_id": genealogy_id,
        "name": f"Name{member_id}",
        "gender": gender,
        "birth_year": 1900 + generation * 25,
        "death_year": "",
        "biography": f"Generation {generation} member",
    }


def generate_data(
    genealogy_count,
    generations,
    min_children,
    max_children,
    seed,
    start_member_id,
    start_marriage_id,
):
    random.seed(seed)
    member_id = start_member_id
    marriage_id = start_marriage_id

    members = []
    parent_child = []
    marriages = []

    for genealogy_id in range(1, genealogy_count + 1):
        father = new_member(member_id, genealogy_id, generation=0, gender="M")
        member_id += 1
        mother = new_member(member_id, genealogy_id, generation=0, gender="F")
        member_id += 1
        members.extend([father, mother])

        couples = [(father, mother)]
        marriages.append(
            {
                "marriage_id": marriage_id,
                "spouse1_id": father["member_id"],
                "spouse2_id": mother["member_id"],
                "start_date": "1970-01-01",
                "end_date": "",
                "status": "active",
            }
        )
        marriage_id += 1

        for gen in range(1, generations + 1):
            next_couples = []
            for f, m in couples:
                child_count = random.randint(min_children, max_children)
                children = []
                for _ in range(child_count):
                    child = new_member(member_id, genealogy_id, generation=gen)
                    member_id += 1
                    members.append(child)
                    children.append(child)
                    parent_child.append(
                        {
                            "parent_id": f["member_id"],
                            "child_id": child["member_id"],
                            "relation_type": "father",
                        }
                    )
                    parent_child.append(
                        {
                            "parent_id": m["member_id"],
                            "child_id": child["member_id"],
                            "relation_type": "mother",
                        }
                    )

                males = [c for c in children if c["gender"] == "M"]
                females = [c for c in children if c["gender"] == "F"]
                pair_count = min(len(males), len(females))
                for i in range(pair_count):
                    spouse1 = males[i]
                    spouse2 = females[i]
                    marriages.append(
                        {
                            "marriage_id": marriage_id,
                            "spouse1_id": spouse1["member_id"],
                            "spouse2_id": spouse2["member_id"],
                            "start_date": f"{1900 + gen * 25 + 20}-01-01",
                            "end_date": "",
                            "status": "active",
                        }
                    )
                    marriage_id += 1
                    next_couples.append((spouse1, spouse2))
            couples = next_couples
            if not couples:
                break

    return members, parent_child, marriages


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate family demo CSV data.")
    parser.add_argument("--out-dir", default="sql/generated", help="Output directory")
    parser.add_argument("--genealogy-count", type=int, default=2)
    parser.add_argument("--generations", type=int, default=4)
    parser.add_argument("--min-children", type=int, default=1)
    parser.add_argument("--max-children", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    members, parent_child, marriages = generate_data(
        genealogy_count=args.genealogy_count,
        generations=args.generations,
        min_children=args.min_children,
        max_children=args.max_children,
        seed=args.seed,
        start_member_id=10000,
        start_marriage_id=10000,
    )

    write_csv(
        out_dir / "member.csv",
        members,
        [
            "member_id",
            "genealogy_id",
            "name",
            "gender",
            "birth_year",
            "death_year",
            "biography",
        ],
    )
    write_csv(
        out_dir / "parent_child.csv",
        parent_child,
        ["parent_id", "child_id", "relation_type"],
    )
    write_csv(
        out_dir / "marriage.csv",
        marriages,
        ["marriage_id", "spouse1_id", "spouse2_id", "start_date", "end_date", "status"],
    )

    print(f"Generated {len(members)} members")
    print(f"Generated {len(parent_child)} parent_child rows")
    print(f"Generated {len(marriages)} marriages")
    print(f"Output dir: {out_dir}")


if __name__ == "__main__":
    main()
