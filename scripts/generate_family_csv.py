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
             min_ch=3, max_ch=5, gen_span=20,
             start_year=None, n_founders=None):
    random.seed(seed)
    mid, marr_id = mid0, marr0
    surname = random.choice(SURNAMES)

    # Determine founding couples and start year
    if n_founders is None:
        n_founders = max(10, target // 30)
    if start_year is None:
        if n_founders >= target:
            start_year = 1990
        else:
            gens = max(5, math.ceil(math.log(target / n_founders) / math.log(1.8)))
            start_year = max(2010 - gens * gen_span, 1400)

    members, pc, marriages = [], [], []
    pc_set, marr_set = set(), set()
    pmap = {}

    # Founding couples
    couples = []
    for _ in range(n_founders):
        by = start_year + random.randint(0, 8)
        f = _member(mid, gid, by, "M", surname); mid += 1
        m = _member(mid, gid, by + random.randint(-3, 2), "F", surname); mid += 1
        members.extend([f, m])
        sy, sm, sd = _clamp(by + 22, 1, 1)
        ed, st = _marriage_end(f, m)
        marriages.append({"marriage_id": marr_id, "spouse1_id": f["member_id"],
                          "spouse2_id": m["member_id"],
                          "start_date": f"{sy}-{sm:02d}-{sd:02d}",
                          "end_date": ed, "status": st})
        marr_set.add((f["member_id"], m["member_id"]))
        marr_id += 1
        couples.append((f, m))

    pool_m, pool_f = [], []

    for gen in range(1, 25):
        if len(members) >= target:
            break
        bb = start_year + gen * gen_span
        if bb > YEAR_CAP - 15:
            break

        # Children from active couples
        for fa, mo in couples:
            n_ch = random.randint(min_ch, max_ch)
            gs = ["M", "F"] if n_ch >= 2 else []
            if n_ch >= 2:
                for _ in range(n_ch - 2):
                    gs.append("M" if random.random() < 0.5 else "F")
                random.shuffle(gs)
            elif n_ch == 1:
                gs = ["M" if random.random() < 0.5 else "F"]

            for g in gs:
                cby = bb + random.randint(-3, gen_span + 3)
                c = _member(mid, gid, cby, g, surname); mid += 1
                members.append(c)
                for pid, rt in [(fa["member_id"], "father"), (mo["member_id"], "mother")]:
                    pair = (pid, c["member_id"])
                    if pair not in pc_set:
                        pc.append({"parent_id": pid, "child_id": c["member_id"],
                                   "relation_type": rt})
                        pc_set.add(pair)
                        pmap.setdefault(c["member_id"], []).append(pid)
                (pool_m if g == "M" else pool_f).append(c)

        # Marriages from generation 4+ (3-gen gap cleared)
        new_couples = []
        if gen >= 4:
            random.shuffle(pool_m)
            random.shuffle(pool_f)
            um, uf = set(), set()
            for i, male in enumerate(pool_m):
                if len(members) >= target:
                    break
                for j, female in enumerate(pool_f):
                    if j in uf:
                        continue
                    my = max(male["birth_year"], female["birth_year"]) + 22
                    my = min(my, YEAR_CAP)
                    if not _eligible(male, female, my, pmap):
                        continue
                    if random.random() > 0.9:
                        continue
                    ed, st = _marriage_end(male, female)
                    sy, sm, sd = _clamp(my, 1, 1)
                    marriages.append({"marriage_id": marr_id,
                                      "spouse1_id": male["member_id"],
                                      "spouse2_id": female["member_id"],
                                      "start_date": f"{sy}-{sm:02d}-{sd:02d}",
                                      "end_date": ed, "status": st})
                    marr_set.add((male["member_id"], female["member_id"]))
                    marr_id += 1
                    new_couples.append((male, female))
                    um.add(i); uf.add(j); break
            pool_m = [x for i, x in enumerate(pool_m) if i not in um]
            pool_f = [x for i, x in enumerate(pool_f) if i not in uf]

        couples = new_couples

    members = members[:target]
    vids = {m["member_id"] for m in members}
    pc = [r for r in pc if r["parent_id"] in vids and r["child_id"] in vids]
    marriages = [r for r in marriages
                 if r["spouse1_id"] in vids and r["spouse2_id"] in vids]
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
    p.add_argument("--min-children", type=int, default=3)
    p.add_argument("--max-children", type=int, default=5)
    p.add_argument("--gen-span", type=int, default=20)
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
    print(f"start_year={sy}, {len(members)} members, {len(pc)} pc, {len(marr)} marriages")


if __name__ == "__main__":
    main()
