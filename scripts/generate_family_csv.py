"""
Generate realistic family tree CSV data.

Timeline: dynamically calculated ~1800-2026 (depending on target size).
Marriage: male 22~60, female 20~55, age gap <= 10, no marriage within 3 generations.
Alive probability: age-dependent (younger = more likely alive in 2026).
"""
import argparse
import csv
import math
import random
from pathlib import Path

YEAR_CAP = 2026
MONTH_CAP = 5

SURNAMES = [
    "赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈",
    "卫", "蒋", "沈", "韩", "杨", "朱", "秦", "许", "何", "张",
    "孔", "曹", "严", "金", "魏", "陶", "姜", "谢", "邹", "苏",
    "潘", "范", "彭", "鲁", "马", "方", "任", "袁", "柳", "唐",
    "薛", "雷", "贺", "汤", "罗", "郝", "安", "常", "于", "傅",
    "齐", "康", "伍", "余", "黄", "萧", "尹", "姚", "汪", "毛",
    "戴", "宋", "熊", "纪", "舒", "屈", "项", "祝", "董", "梁",
    "杜", "阮", "蓝", "席", "季", "麻", "强", "贾", "路", "娄",
    "危", "江", "童", "颜", "郭", "梅", "盛", "林", "刁", "钟",
    "徐", "邱", "骆", "高", "夏", "蔡", "田", "樊", "胡", "凌",
]
GIVEN_M = [
    "伟", "强", "磊", "洋", "勇", "军", "杰", "涛", "明", "辉",
    "鑫", "斌", "波", "宇", "浩", "凯", "健", "俊", "飞", "鹏",
    "志", "刚", "建", "文", "龙", "海", "林", "松", "彬", "泽",
    "天", "达", "奇", "睿", "博", "宏", "毅", "卓", "翔", "远",
    "驰", "烨", "熠", "奕", "鸿", "昊", "宸", "轩", "哲", "晨",
]
GIVEN_F = [
    "芳", "娜", "敏", "静", "丽", "秀", "淑", "惠", "珠", "雅",
    "芝", "玉", "萍", "红", "娥", "玲", "芬", "燕", "彩", "春",
    "菊", "兰", "凤", "洁", "梅", "琳", "素", "云", "莲", "雪",
    "荣", "爱", "霞", "香", "月", "莺", "媛", "艳", "瑞", "佳",
    "怡", "婷", "颖", "欣", "瑶", "薇", "梦", "琪", "蕾", "璐",
]


def _clamp(y, m=1, d=1):
    if y > YEAR_CAP or (y == YEAR_CAP and m > MONTH_CAP):
        return YEAR_CAP, MONTH_CAP, 1
    return y, m, d


def _name(surname, gender):
    pool = GIVEN_M if gender == "M" else GIVEN_F
    g = random.choice(pool)
    if random.random() < 0.3:
        g += random.choice(pool)
    return surname + g


def _surname_of(member):
    name = member.get("name", "")
    return name[0] if name else ""


def _external_surname(clan_surname):
    choices = [s for s in SURNAMES if s != clan_surname]
    return random.choice(choices) if choices else clan_surname


def _alive_prob(birth_year):
    """Age-dependent alive probability in 2026."""
    age = YEAR_CAP - birth_year
    if age <= 30:
        return 0.98
    if age <= 50:
        return 0.90
    if age <= 70:
        return 0.50
    if age <= 85:
        return 0.15
    return 0.02


def _member(mid, gid, birth_year, gender, surname):
    by, _, _ = _clamp(birth_year)
    alive = random.random() < _alive_prob(by)
    if alive:
        dy = ""
    else:
        dy = by + random.randint(40, 90)
        dy, _, _ = _clamp(dy)
        dy = str(max(dy, by + 1))
    return {"member_id": mid, "genealogy_id": gid, "name": _name(surname, gender),
            "gender": gender, "birth_year": by, "death_year": dy, "biography": ""}


def _ancestors(mid, pmap, depth=3):
    anc, q = set(), [mid]
    for _ in range(depth):
        nq = []
        for x in q:
            for p in pmap.get(x, []):
                anc.add(p)
                nq.append(p)
        q = nq
    return anc


def _eligible(m, f, year, pmap):
    am, af = year - m["birth_year"], year - f["birth_year"]
    if am < 22 or am > 60 or af < 20 or af > 55:
        return False
    if abs(m["birth_year"] - f["birth_year"]) > 10:
        return False
    if (m["death_year"] and int(m["death_year"]) <= year) or \
       (f["death_year"] and int(f["death_year"]) <= year):
        return False
    if _ancestors(m["member_id"], pmap) & _ancestors(f["member_id"], pmap):
        return False
    return True


def _marriage_end(s1, s2):
    d1 = int(s1["death_year"]) if s1["death_year"] else 9999
    d2 = int(s2["death_year"]) if s2["death_year"] else 9999
    ey = min(d1, d2)
    if ey < 9999:
        ey, em, ed = _clamp(ey, 6, 1)
        return f"{ey}-{em:02d}-{ed:02d}", "deceased"
    return "", "active"


def generate(target, seed, gid=1, mid0=10000, marr0=10000,
             min_ch=2, max_ch=4, gen_span=20,
             start_year=None, n_founders=None, external_spouse_ratio=0.9,
             male_birth_ratio=0.62):
    random.seed(seed)
    mid, marr_id = mid0, marr0
    clan_surname = random.choice(SURNAMES)

    if n_founders is None:
        if target <= 1000:
            n_founders = 8
        elif target <= 10000:
            n_founders = 10
        else:
            n_founders = 12

    if start_year is None:
        rough_gens = max(8, min(20, math.ceil(math.log(max(2, target / max(1, n_founders))) / math.log(1.7))))
        start_year = max(1600, YEAR_CAP - rough_gens * gen_span - 30)

    members, pc, marriages = [], [], []
    pc_set, marr_set = set(), set()
    pmap = {}

    def _try_add_member(member):
        nonlocal mid
        if len(members) >= target:
            return None
        members.append(member)
        return member

    def _dynamic_children_bounds(gen, max_gens):
        if gen <= max(2, max_gens // 4):
            lo = max(min_ch, 3)
            hi = max(max_ch, 4)
        elif gen <= max(4, (max_gens * 3) // 4):
            lo = min_ch
            hi = max_ch
        else:
            lo = max(1, min_ch - 1)
            hi = max(2, max_ch - 1)
        if hi < lo:
            hi = lo
        return lo, hi

    def _marriage_prob(gen, max_gens):
        if gen <= max(2, max_gens // 3):
            return 0.95
        if gen <= max(4, (max_gens * 2) // 3):
            return 0.90
        return 0.82

    couples = []
    for _ in range(n_founders):
        if len(members) + 2 > target:
            break
        by = start_year + random.randint(0, 8)
        father = _member(mid, gid, by, "M", clan_surname)
        mid += 1
        mother = _member(mid, gid, by + random.randint(-3, 2), "F", _external_surname(clan_surname))
        mid += 1
        members.extend([father, mother])
        sy, sm, sd = _clamp(by + 22, 1, 1)
        ed, st = _marriage_end(father, mother)
        marriages.append({
            "marriage_id": marr_id,
            "spouse1_id": father["member_id"],
            "spouse2_id": mother["member_id"],
            "start_date": f"{sy}-{sm:02d}-{sd:02d}",
            "end_date": ed,
            "status": st,
        })
        marr_set.add((father["member_id"], mother["member_id"]))
        marr_id += 1
        couples.append((father, mother))

    max_generations = max(10, min(40, (YEAR_CAP - start_year) // max(8, gen_span) + 2))
    for gen in range(1, max_generations + 1):
        if len(members) >= target:
            break
        bb = start_year + gen * gen_span
        if bb > YEAR_CAP - 14:
            break

        newborn_m, newborn_f = [], []
        lo, hi = _dynamic_children_bounds(gen, max_generations)

        for father, mother in couples:
            if len(members) >= target:
                break
            n_ch = random.randint(lo, hi)
            genders = []
            if n_ch >= 2:
                genders = ["M", "F"]
                for _ in range(n_ch - 2):
                    genders.append("M" if random.random() < male_birth_ratio else "F")
                random.shuffle(genders)
            elif n_ch == 1:
                genders = ["M" if random.random() < male_birth_ratio else "F"]

            father_surname = _surname_of(father) or clan_surname
            for g in genders:
                if len(members) >= target:
                    break
                cby = bb + random.randint(-3, 3)
                child = _member(mid, gid, cby, g, father_surname)
                mid += 1
                if _try_add_member(child) is None:
                    break

                for pid, rt in [(father["member_id"], "father"), (mother["member_id"], "mother")]:
                    pair = (pid, child["member_id"])
                    if pair not in pc_set:
                        pc.append({"parent_id": pid, "child_id": child["member_id"], "relation_type": rt})
                        pc_set.add(pair)
                        pmap.setdefault(child["member_id"], []).append(pid)

                if g == "M":
                    newborn_m.append(child)
                else:
                    newborn_f.append(child)

        female_pool = list(newborn_f)
        random.shuffle(female_pool)
        next_couples = []
        used_internal_f = set()
        random.shuffle(newborn_m)

        for male in newborn_m:
            if len(members) >= target:
                break

            marry_year = min(max(male["birth_year"] + 22, bb + 12), YEAR_CAP)
            if male["death_year"] and int(male["death_year"]) <= marry_year:
                continue
            if random.random() > _marriage_prob(gen, max_generations):
                continue

            spouse = None
            use_external = random.random() < external_spouse_ratio

            if not use_external:
                for idx, female in enumerate(female_pool):
                    if idx in used_internal_f:
                        continue
                    if not _eligible(male, female, marry_year, pmap):
                        continue
                    spouse = female
                    used_internal_f.add(idx)
                    break

            if spouse is None:
                if len(members) >= target:
                    break
                spouse_birth = male["birth_year"] + random.randint(-4, 3)
                spouse = _member(mid, gid, spouse_birth, "F", _external_surname(clan_surname))
                mid += 1
                if _try_add_member(spouse) is None:
                    break
                if not _eligible(male, spouse, marry_year, pmap):
                    members.pop()
                    continue

            pair = (male["member_id"], spouse["member_id"])
            if pair in marr_set:
                continue

            sy, sm, sd = _clamp(marry_year, 1, 1)
            ed, st = _marriage_end(male, spouse)
            marriages.append({
                "marriage_id": marr_id,
                "spouse1_id": male["member_id"],
                "spouse2_id": spouse["member_id"],
                "start_date": f"{sy}-{sm:02d}-{sd:02d}",
                "end_date": ed,
                "status": st,
            })
            marr_set.add(pair)
            marr_id += 1
            next_couples.append((male, spouse))
        couples = next_couples

    members = members[:target]
    vids = {m["member_id"] for m in members}
    pc = [r for r in pc if r["parent_id"] in vids and r["child_id"] in vids]
    marriages = [r for r in marriages if r["spouse1_id"] in vids and r["spouse2_id"] in vids]
    return members, pc, marriages, start_year


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description="Generate family CSV data.")
    p.add_argument("--out-dir", default="sql/generated")
    p.add_argument("--target", type=int, default=500)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--genealogy-id", type=int, default=1)
    p.add_argument("--start-member-id", type=int, default=10000)
    p.add_argument("--start-marriage-id", type=int, default=10000)
    p.add_argument("--min-children", type=int, default=2)
    p.add_argument("--max-children", type=int, default=4)
    p.add_argument("--gen-span", type=int, default=20)
    p.add_argument("--external-spouse-ratio", type=float, default=0.9,
                   help="Probability of using external (mostly different-surname) spouse")
    p.add_argument("--male-birth-ratio", type=float, default=0.62,
                   help="Probability of male birth (used for growth control)")
    p.add_argument("--start-year", type=int, default=0,
                   help="Start year (0 = auto)")
    p.add_argument("--founders", type=int, default=0,
                   help="Number of founding couples (0 = auto)")
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    members, pc, marr, sy = generate(
        target=args.target, seed=args.seed, gid=args.genealogy_id,
        mid0=args.start_member_id, marr0=args.start_marriage_id,
        min_ch=args.min_children, max_ch=args.max_children,
        gen_span=args.gen_span,
        external_spouse_ratio=args.external_spouse_ratio,
        male_birth_ratio=args.male_birth_ratio,
        start_year=args.start_year if args.start_year > 0 else None,
        n_founders=args.founders if args.founders > 0 else None,
    )
    write_csv(out / "member.csv", members,
              ["member_id", "genealogy_id", "name", "gender",
               "birth_year", "death_year", "biography"])
    write_csv(out / "parent_child.csv", pc,
              ["parent_id", "child_id", "relation_type"])
    write_csv(out / "marriage.csv", marr,
              ["marriage_id", "spouse1_id", "spouse2_id",
               "start_date", "end_date", "status"])
    member_map = {m["member_id"]: m for m in members}
    child_to_parents = {}
    for row in pc:
        child_to_parents.setdefault(row["child_id"], []).append(row["parent_id"])

    roots = [m["member_id"] for m in members if m["member_id"] not in child_to_parents]
    depth = {rid: 1 for rid in roots}
    q = list(roots)
    parent_to_children = {}
    for row in pc:
        parent_to_children.setdefault(row["parent_id"], []).append(row["child_id"])
    while q:
        cur = q.pop(0)
        for ch in parent_to_children.get(cur, []):
            nd = depth[cur] + 1
            if nd > depth.get(ch, 0):
                depth[ch] = nd
                q.append(ch)
    max_depth = max(depth.values()) if depth else 1

    mixed_surname = 0
    for row in marr:
        s1 = member_map.get(row["spouse1_id"])
        s2 = member_map.get(row["spouse2_id"])
        if not s1 or not s2:
            continue
        if _surname_of(s1) != _surname_of(s2):
            mixed_surname += 1
    mixed_ratio = (mixed_surname / len(marr) * 100.0) if marr else 0.0

    years = [m["birth_year"] for m in members if m.get("birth_year") is not None]
    min_year = min(years) if years else None
    max_year = max(years) if years else None
    print(
        f"start_year={sy}, birth_range={min_year}~{max_year}, "
        f"{len(members)} members, {len(pc)} pc, {len(marr)} marriages, "
        f"max_depth={max_depth}, mixed_surname_marriage={mixed_ratio:.1f}%"
    )


if __name__ == "__main__":
    main()
