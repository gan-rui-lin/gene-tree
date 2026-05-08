import argparse
import csv
import math
import random
from pathlib import Path

# ===== Chinese Name Pools =====
SURNAMES = ["赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈",
            "褚", "卫", "蒋", "沈", "韩", "杨", "朱", "秦", "尤", "许",
            "何", "吕", "施", "张", "孔", "曹", "严", "华", "金", "魏",
            "陶", "姜", "戚", "谢", "邹", "苏", "潘", "葛", "范", "彭",
            "鲁", "韦", "昌", "马", "苗", "凤", "花", "方", "俞", "任",
            "袁", "柳", "酆", "鲍", "史", "唐", "费", "廉", "岑", "薛",
            "雷", "贺", "倪", "汤", "滕", "殷", "罗", "毕", "郝", "邬",
            "安", "常", "乐", "于", "时", "傅", "皮", "卞", "齐", "康",
            "伍", "余", "元", "卜", "顾", "孟", "平", "黄", "和", "穆",
            "萧", "尹", "姚", "邵", "湛", "汪", "祁", "毛", "禹", "狄"]

GIVEN_NAMES_MALE = [
    "伟", "强", "磊", "洋", "勇", "军", "杰", "涛", "明", "辉",
    "鑫", "斌", "波", "宇", "浩", "凯", "健", "俊", "飞", "鹏",
    "志", "刚", "建", "文", "龙", "海", "林", "松", "彬", "泽",
    "天", "达", "奇", "思", "睿", "博", "宏", "毅", "卓", "翔",
    "致", "远", "俊", "驰", "雨", "泽", "烨", "熠", "奕", "鸿",
]

GIVEN_NAMES_FEMALE = [
    "芳", "娜", "敏", "静", "丽", "强", "磊", "洋", "秀英", "玉兰",
    "淑", "惠", "珠", "翠", "雅", "芝", "玉", "萍", "红", "娥",
    "玲", "芬", "芳", "燕", "彩", "春", "菊", "兰", "凤", "洁",
    "梅", "琳", "素", "云", "莲", "真", "环", "雪", "荣", "爱",
    "妹", "霞", "香", "月", "莺", "媛", "艳", "瑞", "凡", "佳",
]


def _poisson_sample(lam):
    """Knuth's algorithm for Poisson sampling."""
    l = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p < l:
            return k - 1


def _poisson_children(avg, min_c, max_c):
    """Poisson-distributed child count clamped to [min_c, max_c]."""
    val = _poisson_sample(avg)
    return max(min_c, min(max_c, val))


def _uniform_children(min_c, max_c):
    return random.randint(min_c, max_c)


def new_member(member_id, genealogy_id, generation, gender, surname,
               alive_prob, base_year=1900, gen_span=25):
    """Create a member dict with Chinese name and realistic life dates."""
    given_pool = GIVEN_NAMES_MALE if gender == "M" else GIVEN_NAMES_FEMALE
    given = random.choice(given_pool)
    # 30% chance of two-character given name
    if random.random() < 0.3:
        given += random.choice(given_pool)
    name = surname + given

    birth_year = base_year + generation * gen_span + random.randint(0, 5)
    is_alive = random.random() < alive_prob
    death_year = "" if is_alive else birth_year + random.randint(40, 90)

    return {
        "member_id": member_id,
        "genealogy_id": genealogy_id,
        "name": name,
        "gender": gender,
        "birth_year": birth_year,
        "death_year": death_year,
        "biography": f"第{generation}代",
    }


def generate_data(
    genealogy_count,
    generations,
    min_children,
    max_children,
    seed,
    start_member_id,
    start_marriage_id,
    gender_ratio,
    marriage_prob,
    children_dist,
    avg_children,
    alive_prob,
):
    random.seed(seed)
    member_id = start_member_id
    marriage_id = start_marriage_id

    members = []
    parent_child = []
    marriages = []
    # Track existing parent-child pairs for duplicate protection
    pc_set = set()
    # Track existing marriage pairs for duplicate protection
    marriage_set = set()

    child_fn = (_poisson_children if children_dist == "poisson"
                else _uniform_children)

    for genealogy_id in range(1, genealogy_count + 1):
        surname = random.choice(SURNAMES)

        # Create founding couple
        father = new_member(member_id, genealogy_id, 0, "M", surname, alive_prob)
        member_id += 1
        mother = new_member(member_id, genealogy_id, 0, "F", surname, alive_prob)
        member_id += 1
        members.extend([father, mother])

        couples = [(father, mother)]
        marriages.append({
            "marriage_id": marriage_id,
            "spouse1_id": father["member_id"],
            "spouse2_id": mother["member_id"],
            "start_date": f"{1900 + random.randint(0, 5)}-01-01",
            "end_date": "",
            "status": "active",
        })
        marriage_set.add((father["member_id"], mother["member_id"]))
        marriage_id += 1

        for gen in range(1, generations + 1):
            next_couples = []
            for f, m in couples:
                if children_dist == "poisson":
                    child_count = _poisson_children(avg_children, min_children, max_children)
                else:
                    child_count = _uniform_children(min_children, max_children)

                children = []
                for _ in range(child_count):
                    # Gender based on ratio
                    gender = "M" if random.random() < gender_ratio else "F"
                    child = new_member(member_id, genealogy_id, gen, gender, surname, alive_prob)
                    member_id += 1
                    members.append(child)
                    children.append(child)

                    # Anomaly protection: prevent self-loop
                    if f["member_id"] == child["member_id"]:
                        continue
                    if m["member_id"] == child["member_id"]:
                        continue

                    # Anomaly protection: prevent duplicate parent-child
                    pair_f = (f["member_id"], child["member_id"])
                    pair_m = (m["member_id"], child["member_id"])
                    if pair_f not in pc_set:
                        parent_child.append({
                            "parent_id": f["member_id"],
                            "child_id": child["member_id"],
                            "relation_type": "father",
                        })
                        pc_set.add(pair_f)
                    if pair_m not in pc_set:
                        parent_child.append({
                            "parent_id": m["member_id"],
                            "child_id": child["member_id"],
                            "relation_type": "mother",
                        })
                        pc_set.add(pair_m)

                # Pair children into couples based on marriage probability
                males = [c for c in children if c["gender"] == "M"]
                females = [c for c in children if c["gender"] == "F"]
                random.shuffle(males)
                random.shuffle(females)
                pair_count = min(len(males), len(females))
                for i in range(pair_count):
                    if random.random() > marriage_prob:
                        continue
                    spouse1 = males[i]
                    spouse2 = females[i]

                    # Anomaly protection: prevent duplicate marriage
                    m_pair = (spouse1["member_id"], spouse2["member_id"])
                    m_pair_rev = (spouse2["member_id"], spouse1["member_id"])
                    if m_pair in marriage_set or m_pair_rev in marriage_set:
                        continue

                    marriages.append({
                        "marriage_id": marriage_id,
                        "spouse1_id": spouse1["member_id"],
                        "spouse2_id": spouse2["member_id"],
                        "start_date": f"{1900 + gen * 25 + 20}-01-01",
                        "end_date": "",
                        "status": "active",
                    })
                    marriage_set.add(m_pair)
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
    parser.add_argument("--gender-ratio", type=float, default=0.5,
                        help="Probability of male child (0-1, default 0.5)")
    parser.add_argument("--marriage-probability", type=float, default=0.8,
                        help="Probability a child pairs into marriage (0-1, default 0.8)")
    parser.add_argument("--children-dist", choices=["uniform", "poisson"], default="uniform",
                        help="Children count distribution: uniform or poisson (default uniform)")
    parser.add_argument("--avg-children", type=float, default=2.0,
                        help="Average children per couple for poisson distribution (default 2.0)")
    parser.add_argument("--alive-probability", type=float, default=0.3,
                        help="Probability a member is still alive, i.e. death_year is empty (0-1, default 0.3)")
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
        gender_ratio=args.gender_ratio,
        marriage_prob=args.marriage_probability,
        children_dist=args.children_dist,
        avg_children=args.avg_children,
        alive_prob=args.alive_probability,
    )

    write_csv(
        out_dir / "member.csv",
        members,
        ["member_id", "genealogy_id", "name", "gender", "birth_year", "death_year", "biography"],
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
